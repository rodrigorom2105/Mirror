"""Perfil emocional consolidado — memoria de largo plazo (nivel B).

Síntesis incremental de quién es el usuario emocionalmente. Se actualiza en
O(1)/O(ventana) tras cada entrada, nunca recorre el histórico completo. Vive
en SQLite (tabla `profile`, una sola fila). Es un derivado reconstruible
desde ChromaDB — ver `scripts/rebuild_profile.py`.

La pieza clave son las `fuentes_de_bienestar`: actividades, lugares, personas
y disparadores tomados de las entradas positivas del usuario. Es lo que
alimenta las recomendaciones "sin inventar".
"""
import json
import os
from datetime import date, datetime

from services.db import get_conn

_VENTANA_TENDENCIA = int(os.getenv("PROFILE_TREND_WINDOW", "7"))
_SYNTHESIS_EVERY = int(os.getenv("PROFILE_SYNTHESIS_EVERY", "5"))
_TOP_N = 5

_CUADRANTES_POSITIVOS = {"verde", "amarillo"}
_CUADRANTES_NEGATIVOS = {"rojo", "azul"}


def _default_profile() -> dict:
    return {
        "version": 1,
        "entry_count": 0,
        "first_entry_at": None,
        "last_entry_at": None,
        "cuadrante_counts": {"rojo": 0, "amarillo": 0, "azul": 0, "verde": 0},
        "baseline": {"valencia": 0.0, "energia": 0.0, "intensidad": 0.0},
        "tendencia_reciente": {"ventana": _VENTANA_TENDENCIA, "valencia": 0.0,
                               "energia": 0.0, "cuadrante_dominante": None},
        "_tendencia_buffer": [],
        "disparadores_recurrentes": {},
        "personas_recurrentes": {},
        "lugares_recurrentes": {},
        "fuentes_de_bienestar": {"actividades": {}, "lugares": {},
                                 "personas": {}, "disparadores": {}},
        "registro": {"racha_dias": 0, "ultima_fecha": None, "dias_activos": 0},
        "hitos": [],
        "sintesis_narrativa": "",
        "sintesis_actualizada_at": None,
    }


# ─── Lectura / escritura ──────────────────────────────────────────────────

def get_profile() -> dict:
    """Devuelve el perfil consolidado (o uno vacío si aún no existe)."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT data FROM profile WHERE id = 1").fetchone()
    finally:
        conn.close()
    if row is None:
        return _default_profile()
    profile = _default_profile()
    profile.update(json.loads(row["data"]))
    return profile


def _save_profile(profile: dict) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO profile (id, data, entry_count, updated_at) "
            "VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data, "
            "entry_count=excluded.entry_count, updated_at=excluded.updated_at",
            (json.dumps(profile, ensure_ascii=False), profile["entry_count"],
             datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# ─── Helpers ──────────────────────────────────────────────────────────────

def _norm(s) -> str:
    return (s or "").strip().lower() if isinstance(s, str) else ""


def _bump(counter: dict, key, n: int = 1) -> None:
    key = _norm(key)
    if key:
        counter[key] = counter.get(key, 0) + n


def _top(counter: dict, n: int = _TOP_N) -> list:
    return [k for k, _ in sorted(counter.items(), key=lambda kv: kv[1],
                                 reverse=True)[:n]]


# ─── Actualización incremental ────────────────────────────────────────────

def update_profile_with_entry(ruler: dict) -> dict:
    """Integra una entrada nueva en el perfil. Incremental, sin recorrer todo."""
    p = get_profile()
    p["entry_count"] += 1
    n = p["entry_count"]
    saved_at = ruler.get("saved_at") or datetime.utcnow().isoformat()
    if p["first_entry_at"] is None:
        p["first_entry_at"] = saved_at
    p["last_entry_at"] = saved_at

    cuad = ruler.get("cuadrante", "")
    if cuad in p["cuadrante_counts"]:
        p["cuadrante_counts"][cuad] += 1

    val = float(ruler.get("valencia") or 0.0)
    ene = float(ruler.get("energia") or 0.0)
    inten = float(ruler.get("intensidad") or 0.0)

    # Baseline por media móvil acumulada (running mean) — O(1), sin histórico.
    b = p["baseline"]
    b["valencia"] += (val - b["valencia"]) / n
    b["energia"] += (ene - b["energia"]) / n
    b["intensidad"] += (inten - b["intensidad"]) / n

    # Tendencia reciente: ventana móvil de las últimas N entradas.
    buf = p["_tendencia_buffer"]
    buf.append({"valencia": val, "energia": ene, "cuadrante": cuad})
    del buf[:-_VENTANA_TENDENCIA]
    tr = p["tendencia_reciente"]
    tr["valencia"] = sum(x["valencia"] for x in buf) / len(buf)
    tr["energia"] = sum(x["energia"] for x in buf) / len(buf)
    cuad_counts: dict = {}
    for x in buf:
        cuad_counts[x["cuadrante"]] = cuad_counts.get(x["cuadrante"], 0) + 1
    tr["cuadrante_dominante"] = (max(cuad_counts, key=cuad_counts.get)
                                 if cuad_counts else None)

    # Recurrencias (todo el espectro emocional).
    ctx = ruler.get("contexto") if isinstance(ruler.get("contexto"), dict) else {}
    _bump(p["disparadores_recurrentes"], ruler.get("disparador", ""))
    for persona in (ctx.get("personas") or []):
        _bump(p["personas_recurrentes"], persona)
    _bump(p["lugares_recurrentes"], ctx.get("lugar", ""))

    # Fuentes de bienestar: SOLO de entradas positivas con buena valencia.
    # Esto es lo que el sistema podrá recomendar "sin inventar".
    if cuad in _CUADRANTES_POSITIVOS and val >= 0.3:
        fb = p["fuentes_de_bienestar"]
        _bump(fb["actividades"], ctx.get("actividad", ""))
        _bump(fb["lugares"], ctx.get("lugar", ""))
        for persona in (ctx.get("personas") or []):
            _bump(fb["personas"], persona)
        _bump(fb["disparadores"], ruler.get("disparador", ""))

    _update_registro(p, saved_at)
    _detect_hitos(p, ruler, saved_at)

    _save_profile(p)
    return p


def _update_registro(p: dict, saved_at: str) -> None:
    """Actualiza la racha de días registrando."""
    reg = p["registro"]
    try:
        d = datetime.fromisoformat(saved_at).date()
    except (ValueError, TypeError):
        d = date.today()
    d_iso = d.isoformat()
    ultima = reg["ultima_fecha"]
    if ultima == d_iso:
        return  # mismo día — no cambia la racha
    if ultima is None:
        reg["racha_dias"] = 1
        reg["dias_activos"] = 1
    else:
        try:
            delta = (d - date.fromisoformat(ultima)).days
        except ValueError:
            delta = 99
        if delta == 1:
            reg["racha_dias"] += 1
        elif delta > 1:
            reg["racha_dias"] = 1
        reg["dias_activos"] += 1
    reg["ultima_fecha"] = d_iso


def _detect_hitos(p: dict, ruler: dict, saved_at: str) -> None:
    """Registra eventos notables del perfil (reglas simples, sin LLM)."""
    hitos = p["hitos"]
    if p["registro"]["racha_dias"] in (7, 14, 30):
        hitos.append({"tipo": "racha_registro", "fecha": saved_at,
                      "detalle": f"{p['registro']['racha_dias']} días seguidos registrando"})
    if ruler.get("crisis_flag"):
        hitos.append({"tipo": "crisis", "fecha": saved_at,
                      "detalle": "Se detectó lenguaje de crisis"})
    del hitos[:-20]  # mantener acotado


# ─── Lecturas derivadas ───────────────────────────────────────────────────

def get_wellbeing_sources(n: int = _TOP_N) -> dict:
    """Top fuentes de bienestar — lo que al usuario ya le ha hecho bien."""
    fb = get_profile()["fuentes_de_bienestar"]
    return {
        "actividades": _top(fb["actividades"], n),
        "lugares": _top(fb["lugares"], n),
        "personas": _top(fb["personas"], n),
        "disparadores": _top(fb["disparadores"], n),
    }


def get_profile_summary_for_prompt() -> str:
    """Versión compacta del perfil en texto, para inyectar al LLM."""
    p = get_profile()
    if p["entry_count"] == 0:
        return "Aún no hay registros suficientes para un perfil."
    cc = p["cuadrante_counts"]
    dom = max(cc, key=cc.get) if any(cc.values()) else "—"
    tr = p["tendencia_reciente"]
    lineas = [
        f"Registros totales: {p['entry_count']}.",
        f"Cuadrante dominante: {dom}.",
        f"Baseline — valencia {p['baseline']['valencia']:.2f}, "
        f"energía {p['baseline']['energia']:.2f}.",
        f"Tendencia reciente: cuadrante {tr['cuadrante_dominante']}, "
        f"valencia {tr['valencia']:.2f}.",
        f"Racha de registro: {p['registro']['racha_dias']} día(s).",
    ]
    disp = _top(p["disparadores_recurrentes"], 3)
    if disp:
        lineas.append(f"Disparadores recurrentes: {', '.join(disp)}.")
    fb = p["fuentes_de_bienestar"]
    bien = _top(fb["actividades"], 3) + _top(fb["lugares"], 2)
    if bien:
        lineas.append(f"Le ha hecho bien: {', '.join(bien)}.")
    if p["sintesis_narrativa"]:
        lineas.append(f"Síntesis: {p['sintesis_narrativa']}")
    return "\n".join(lineas)


# ─── Síntesis narrativa (usa LLM — operación cara, dosificada) ────────────

def should_regenerate_narrative(profile: dict) -> bool:
    """True si toca regenerar la síntesis (cada K entradas)."""
    n = profile.get("entry_count", 0)
    return n >= 3 and n % _SYNTHESIS_EVERY == 0


def regenerate_narrative() -> None:
    """Regenera la síntesis narrativa con el LLM. Cara — correr en background.

    Nunca debe romper el flujo: cualquier fallo se traga (la síntesis es
    un extra, no un dato crítico).
    """
    p = get_profile()
    if p["entry_count"] < 3:
        return
    try:
        from services.llm_service import _load_prompt, _ollama_generate
        system = _load_prompt("profile_synthesis.txt")
        narrativa = _ollama_generate(system, get_profile_summary_for_prompt())
        p = get_profile()  # relee por si cambió mientras corría el LLM
        p["sintesis_narrativa"] = narrativa.strip()
        p["sintesis_actualizada_at"] = datetime.utcnow().isoformat()
        _save_profile(p)
    except Exception:  # noqa: BLE001 - la síntesis es opcional
        pass
