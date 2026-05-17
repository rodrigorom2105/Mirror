"""Feedback emocional contextual — se genera al registrar una emoción.

Reemplaza al reasoning_pipeline para el feedback de registro: aquí no hay
compuerta, el feedback se genera SIEMPRE en uno de dos modos (apoyo / ligero).
"""
from datetime import datetime

from services.emotion_catalog import emotion_position, position_intensity

# Pesos de la intensidad dinámica.
_W_EMOCION = 0.60
_W_CONTENIDO = 0.40
_W_PRIMARIA = 0.70
_W_SECUNDARIAS = 0.30

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
