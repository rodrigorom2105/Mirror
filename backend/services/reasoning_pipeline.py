"""Pipeline de razonamiento — el embudo de decisión de Mirror.

Sigue la prioridad del usuario: entender → interpretar → detectar → decidir →
generar. Los pasos 1-4 son deterministas y baratos; el paso 5 (LLM) solo corre
si el gate del paso 4 dio luz verde. Así el sistema "no genera por generar":
la mayoría de las veces decide callar.
"""
import os
import time
from dataclasses import asdict, dataclass, field

from services.signals_engine import compute_signals

_COOLDOWN_HORAS = float(os.getenv("COMPANION_COOLDOWN_HOURS", "6"))
_MIN_ENTRADAS = int(os.getenv("COMPANION_MIN_ENTRIES", "3"))
_RELEVANCE_FLOOR = float(os.getenv("COMPANION_RELEVANCE_FLOOR", "0.5"))

# Cooldown in-memory (single-user, hackathon — se reinicia con el server).
_ultima_intervencion_ts = 0.0


@dataclass
class CompanionResult:
    intervenir: bool
    modo: str  # silencio | recomendacion | reflexion
    mensaje: str | None = None
    senal: dict | None = None
    estado: str = ""
    razonamiento: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _en_cooldown() -> bool:
    return (time.time() - _ultima_intervencion_ts) < _COOLDOWN_HORAS * 3600


def _marcar_intervencion() -> None:
    global _ultima_intervencion_ts
    _ultima_intervencion_ts = time.time()


# ─── Paso 3: detectar estado ──────────────────────────────────────────────

def classify_state(signals: list) -> str:
    """Clasifica el estado emocional a partir de las señales detectadas."""
    tipos = {s.tipo for s in signals}
    if "emocion_negativa_intensa" in tipos or "racha_negativa" in tipos:
        return "en_dificultad"
    if "intensidad_anomala" in tipos:
        return "volatil"
    if "tendencia_valencia" in tipos:
        t = next(s for s in signals if s.tipo == "tendencia_valencia")
        return "en_mejora" if t.evidencia.get("delta", 0) > 0 else "en_dificultad"
    if "ausencia_registro" in tipos:
        return "desconectado"
    return "estable"


# ─── Paso 4: el gate ──────────────────────────────────────────────────────

def decide_intervention(trigger: str, top, estado: str) -> dict:
    """Decide si vale la pena intervenir. Aquí muere la mayoría de los casos."""
    if _en_cooldown():
        return {"intervenir": False, "modo": "silencio",
                "motivo": "cooldown activo (intervención reciente)"}
    # La señal central siempre amerita acompañamiento.
    if top.tipo == "emocion_negativa_intensa":
        return {"intervenir": True, "modo": "recomendacion",
                "motivo": "emoción negativa intensa: se recogerá contexto y se sugerirá"}
    # Interrumpir justo tras registrar es más invasivo → umbral más alto.
    umbral = _RELEVANCE_FLOOR + (0.15 if trigger == "post_entry" else 0.0)
    if top.score < umbral:
        return {"intervenir": False, "modo": "silencio",
                "motivo": f"señal por debajo del umbral ({top.score} < {umbral:.2f})"}
    if estado == "estable":
        return {"intervenir": False, "modo": "silencio",
                "motivo": "estado estable: nada nuevo que aportar"}
    modo = "recomendacion" if estado == "en_dificultad" else "reflexion"
    return {"intervenir": True, "modo": modo,
            "motivo": f"señal relevante ({top.tipo})"}


# ─── Pipeline completo ────────────────────────────────────────────────────

def run_companion_pipeline(trigger: str = "on_open", entries=None) -> CompanionResult:
    """Ejecuta el embudo de 5 pasos. `trigger`: on_open | post_entry | manual."""
    razon = []

    # Paso 1 — Entender contexto
    if entries is None:
        from services.memory_service import get_history
        entries = get_history(limit=100)
    razon.append(f"[1] Entender: {len(entries)} entradas en contexto.")
    if len(entries) < _MIN_ENTRADAS:
        razon.append("[1] Datos insuficientes — no se interpreta lo que aún no se conoce.")
        return CompanionResult(False, "silencio", razonamiento=razon)
    signals = compute_signals(entries)
    razon.append(f"[1] Señales: {[s.tipo for s in signals] or 'ninguna'}.")

    # Paso 2 — Interpretar relevancia
    if not signals:
        razon.append("[2] Sin señales relevantes.")
        return CompanionResult(False, "silencio", razonamiento=razon)
    top = signals[0]
    razon.append(f"[2] Señal principal: {top.tipo} "
                  f"(score {top.score}, urgencia {top.urgencia}).")

    # Paso 3 — Detectar estado
    estado = classify_state(signals)
    razon.append(f"[3] Estado emocional: {estado}.")

    # Paso 4 — Decidir (gate)
    decision = decide_intervention(trigger, top, estado)
    razon.append(f"[4] Decisión: {decision['motivo']}.")
    if not decision["intervenir"]:
        return CompanionResult(False, "silencio", senal=top.to_dict(),
                               estado=estado, razonamiento=razon)

    # Paso 5 — Generar (LLM, solo si el gate aprobó)
    try:
        mensaje = _generar_mensaje(decision["modo"], top, entries)
    except Exception as exc:  # noqa: BLE001 - un fallo del LLM no debe romper
        razon.append(f"[5] Error generando el mensaje: {exc}")
        return CompanionResult(False, "silencio", senal=top.to_dict(),
                               estado=estado, razonamiento=razon)
    razon.append(f"[5] Mensaje generado (modo {decision['modo']}).")
    _marcar_intervencion()
    return CompanionResult(True, decision["modo"], mensaje.strip(),
                           top.to_dict(), estado, razon)


# ─── Paso 5: generación (LLM) ─────────────────────────────────────────────

def _generar_mensaje(modo: str, signal, entries: list) -> str:
    from services.llm_service import generate_companion
    if modo == "recomendacion":
        return generate_companion(_bloque_recomendacion(signal, entries))
    return generate_companion(_bloque_reflexion(signal))


def _bloque_recomendacion(signal, entries: list) -> str:
    """Evidencia para una recomendación basada SOLO en lo que el usuario conoce."""
    from services.memory_service import retrieve_relevant
    from services.profile_service import get_wellbeing_sources

    fuentes = get_wellbeing_sources(5)
    ev = signal.evidencia
    lines = [f"SEÑAL: {signal.titulo}"]
    if ev.get("emocion"):
        lines.append(f"EMOCIÓN ACTUAL: {ev['emocion']} "
                      f"(intensidad {ev.get('intensidad', '?')}/10)")
    if ev.get("disparador"):
        lines.append(f"DISPARADOR: {ev['disparador']}")

    conocidas = []
    for cat in ("actividades", "lugares", "personas"):
        conocidas.extend(fuentes.get(cat, []))
    if conocidas:
        lines.append("COSAS QUE YA LE HAN HECHO BIEN (sugiere solo estas, "
                      "nunca inventes): " + "; ".join(conocidas))
    else:
        lines.append("COSAS QUE YA LE HAN HECHO BIEN: sin datos — no "
                      "recomiendes actividades, solo acompaña con calidez.")

    try:
        positivas = retrieve_relevant(ev.get("emocion") or "bienestar",
                                      top_k=3, cuadrantes=["verde", "amarillo"])
    except Exception:  # noqa: BLE001
        positivas = []
    if positivas:
        lines.append("MOMENTOS POSITIVOS PASADOS DEL USUARIO:")
        for p in positivas:
            lines.append(f"- {p.get('resumen', '')}")
    return "\n".join(lines)


def _bloque_reflexion(signal) -> str:
    lines = [f"SEÑAL: {signal.titulo}"]
    for k, v in signal.evidencia.items():
        lines.append(f"{k}: {v}")
    lines.append("MODO: reflexión — refleja el patrón observado y, si encaja, "
                  "haz una pregunta abierta. No recomiendes actividades.")
    return "\n".join(lines)
