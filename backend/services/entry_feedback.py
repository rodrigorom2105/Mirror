"""Feedback emocional contextual — se genera al registrar una emoción.

Reemplaza al reasoning_pipeline para el feedback de registro: aquí no hay
compuerta, el feedback se genera SIEMPRE en uno de dos modos (apoyo / ligero).
"""
import os
from datetime import datetime

from services.emotion_catalog import emotion_position, position_intensity

# Pesos de la intensidad dinámica.
_W_EMOCION = 0.60
_W_CONTENIDO = 0.40
_W_PRIMARIA = 0.70
_W_SECUNDARIAS = 0.30

# Similitud mínima para tratar una entrada pasada como "contexto suficiente"
# y ofrecérsela al LLM. Por debajo del umbral el feedback se queda con el
# registro actual y el perfil. Tunable por entorno sin tocar código.
_MIN_CONTEXT_SIM = float(os.getenv("FEEDBACK_CONTEXT_MIN_SIM", "0.45"))

_CUADRANTES_NEGATIVOS = {"rojo", "azul"}
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ─── Intensidad dinámica ──────────────────────────────────────────────────

def _intensidad_emocion(selected_emotion, secundarias):
    """Intensidad 1-10 derivada de la posición de las emociones, o None."""
    pos = emotion_position(selected_emotion)
    if pos is None:
        return None
    primaria = position_intensity(pos)
    sec = []
    for s in secundarias or []:
        p = emotion_position(s)
        if p is not None:
            sec.append(position_intensity(p))
    if sec:
        return _W_PRIMARIA * primaria + _W_SECUNDARIAS * (sum(sec) / len(sec))
    return primaria


def compute_intensity(ruler: dict, selected_emotion: str) -> int:
    """Intensidad final 1-10: 60% emociones seleccionadas + 40% contenido."""
    contenido = min(max(float(ruler.get("intensidad") or 0), 1.0), 10.0)
    emocion = _intensidad_emocion(selected_emotion,
                                  ruler.get("emociones_secundarias"))
    if emocion is None:
        final = contenido
    else:
        final = _W_EMOCION * emocion + _W_CONTENIDO * contenido
    return min(max(round(final), 1), 10)


# ─── Contexto temporal ────────────────────────────────────────────────────

def franja_horaria(client_time: str | None) -> tuple[str, str]:
    """(franja, día de la semana) a partir de un ISO 8601 con offset.

    Si `client_time` falta o es inválido, usa la hora local del servidor.
    """
    try:
        dt = datetime.fromisoformat(client_time)
    except (ValueError, TypeError):
        dt = datetime.now()
    h = dt.hour
    franja = ("madrugada" if h < 6 else "mañana" if h < 12
              else "tarde" if h < 19 else "noche")
    return franja, _DIAS[dt.weekday()]


# ─── Selección de modo ────────────────────────────────────────────────────

def select_mode(ruler: dict) -> str:
    """'apoyo' si la emoción es negativa e intensa; 'ligero' en otro caso."""
    cuad = (ruler.get("cuadrante") or "").strip().lower()
    intensidad = float(ruler.get("intensidad") or 0)
    if cuad in _CUADRANTES_NEGATIVOS and intensidad > 5:
        return "apoyo"
    return "ligero"


# ─── Generación del feedback (LLM) ────────────────────────────────────────

_FALLBACK = ("Gracias por registrar cómo te sientes. "
             "Tomarte este momento ya es una forma de cuidarte.")


def _build_evidence(ruler: dict, modo: str, client_time) -> str:
    """Arma el bloque de evidencia estructurada para el prompt del feedback."""
    from services.memory_service import (
        format_context_block,
        get_helpful_feedback_examples,
        retrieve_relevant,
    )
    from services.profile_service import get_wellbeing_sources

    franja, dia = franja_horaria(client_time)
    lines = [
        f"MODO: {modo}",
        f"EMOCIÓN: {ruler.get('emocion_primaria', '?')} "
        f"(cuadrante {ruler.get('cuadrante', '?')}, "
        f"intensidad {ruler.get('intensidad', '?')}/10)",
    ]
    if ruler.get("disparador"):
        lines.append(f"DISPARADOR: {ruler['disparador']}")
    if ruler.get("resumen"):
        lines.append(f"RESUMEN: {ruler['resumen']}")
    lines.append(f"MOMENTO: {franja}, {dia}")

    try:
        fuentes = get_wellbeing_sources(5)
        conocidas = []
        for cat in ("actividades", "lugares", "personas"):
            conocidas.extend(fuentes.get(cat, []))
    except Exception:  # noqa: BLE001
        conocidas = []
    if conocidas:
        lines.append("COSAS QUE YA LE HAN HECHO BIEN (sugiere solo estas, "
                     "nunca inventes): " + "; ".join(conocidas))
    else:
        lines.append("COSAS QUE YA LE HAN HECHO BIEN: sin datos — no "
                     "recomiendes actividades, solo acompaña con calidez.")

    # ENTRADAS PASADAS RELACIONADAS — contexto del propio historial. Solo se
    # ofrece si hay similitud real; si no, el feedback se centra en el ahora.
    try:
        consulta = " ".join(filter(None, [
            ruler.get("resumen", ""),
            ruler.get("emocion_primaria", ""),
            ruler.get("disparador", ""),
        ])).strip()
        relacionadas = retrieve_relevant(consulta, top_k=4) if consulta else []
        relacionadas = [e for e in relacionadas
                        if e.get("_sim", 0) >= _MIN_CONTEXT_SIM][:2]
    except Exception:  # noqa: BLE001
        relacionadas = []
    if relacionadas:
        lines.append("ENTRADAS PASADAS RELACIONADAS (de su propio historial; "
                      "menciónalas SOLO si conectan de verdad con este "
                      "registro, sin forzarlo):")
        lines.append(format_context_block(relacionadas))

    try:
        ejemplos = get_helpful_feedback_examples(2)
    except Exception:  # noqa: BLE001
        ejemplos = []
    if ejemplos:
        lines.append("MENSAJES QUE ANTES LE AYUDARON (inspírate en su tono):")
        for m in ejemplos:
            lines.append(f"- {m}")
    return "\n".join(lines)


def generate_entry_feedback(ruler: dict, selected_emotion: str,
                            client_time) -> dict:
    """Genera el feedback contextual de Mira para una entrada recién analizada.

    Devuelve {'mensaje': str, 'modo': 'apoyo'|'ligero'}. Nunca lanza: ante
    cualquier fallo del LLM devuelve un mensaje de respaldo cálido.
    """
    modo = select_mode(ruler)
    try:
        from services.llm_service import _load_prompt, _ollama_generate
        system = _load_prompt("entry_feedback.txt")
        evidence = _build_evidence(ruler, modo, client_time)
        mensaje = _ollama_generate(system, evidence, temperature=0.7,
                                   num_predict=180).strip()
        if not mensaje:
            mensaje = _FALLBACK
    except Exception:  # noqa: BLE001 - el feedback nunca debe romper el análisis
        mensaje = _FALLBACK
    return {"mensaje": mensaje, "modo": modo}
