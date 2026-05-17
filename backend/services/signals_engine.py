"""Motor de señales — detección determinista de patrones emocionales.

Sin LLM: pura estadística sobre las entradas RULER ya estructuradas. Corre en
milisegundos. Cada detector devuelve una `Signal` (con `score` de relevancia y
`urgencia`) o `None`. `classify_state` deriva el estado global de las señales.

Las entradas llegan ordenadas por fecha DESCENDENTE (la más reciente primero),
tal como las devuelve `memory_service.get_history`.
"""
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

# Umbrales tunables vía .env (para ajustar en vivo durante la demo).
INTENSIDAD_UMBRAL = float(os.getenv("SIGNAL_INTENSITY_THRESHOLD", "5"))
RACHA_MIN = int(os.getenv("SIGNAL_STREAK_MIN", "3"))
RECURRENCIA_MIN = int(os.getenv("SIGNAL_RECURRENCE_MIN", "3"))

_NEG = {"rojo", "azul"}
_POS = {"verde", "amarillo"}


@dataclass
class Signal:
    tipo: str
    titulo: str
    evidencia: dict = field(default_factory=dict)
    score: float = 0.0       # relevancia 0..1
    urgencia: float = 0.0    # qué tan "ahora" es, 0..1
    ventana: str = ""
    detectada_en: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _ts(e: dict) -> float:
    return e.get("ts") or 0.0


def _dias_desde(e: dict) -> int:
    ts = _ts(e)
    if not ts:
        return 999
    return max(int((datetime.utcnow().timestamp() - ts) / 86400), 0)


def _ahora() -> str:
    return datetime.utcnow().isoformat()


def _por_dia(entries: list) -> dict:
    """Agrupa entradas por fecha (date → lista de entradas)."""
    dias: dict = {}
    for e in entries:
        ts = _ts(e)
        if not ts:
            continue
        d = datetime.utcfromtimestamp(ts).date()
        dias.setdefault(d, []).append(e)
    return dias


# ─── Detectores ───────────────────────────────────────────────────────────

def detect_emocion_negativa_intensa(entries: list):
    """Señal CENTRAL: la última entrada es negativa e intensa (> umbral).

    Es la que dispara el acompañamiento con recomendaciones de bienestar.
    """
    if not entries:
        return None
    e = entries[0]
    cuad = e.get("cuadrante", "")
    inten = float(e.get("intensidad") or 0)
    if cuad in _NEG and inten > INTENSIDAD_UMBRAL:
        score = min(0.6 + (inten - INTENSIDAD_UMBRAL) / 10, 1.0)
        return Signal(
            tipo="emocion_negativa_intensa",
            titulo=f"Registraste {e.get('emocion_primaria', 'una emoción difícil')} "
                   f"con intensidad {int(inten)}/10",
            evidencia={
                "emocion": e.get("emocion_primaria"),
                "cuadrante": cuad,
                "intensidad": inten,
                "disparador": e.get("disparador"),
                "entry_id": e.get("id"),
            },
            score=round(score, 2),
            urgencia=round(min(inten / 10, 1.0), 2),
            ventana="ahora",
            detectada_en=_ahora(),
        )
    return None


def detect_streak(entries: list):
    """Racha de N≥3 días consecutivos en emociones del mismo signo."""
    dias = _por_dia(entries)
    if not dias:
        return None
    fechas = sorted(dias.keys(), reverse=True)

    def signo(d):
        cuads = [x.get("cuadrante") for x in dias[d]]
        neg = sum(1 for c in cuads if c in _NEG)
        pos = sum(1 for c in cuads if c in _POS)
        return "neg" if neg > pos else ("pos" if pos > neg else None)

    s0 = signo(fechas[0])
    if s0 is None:
        return None
    racha = 1
    for i in range(1, len(fechas)):
        if (fechas[i - 1] - fechas[i]).days == 1 and signo(fechas[i]) == s0:
            racha += 1
        else:
            break
    if racha < RACHA_MIN:
        return None
    es_neg = s0 == "neg"
    return Signal(
        tipo="racha_negativa" if es_neg else "racha_positiva",
        titulo=f"{racha} días seguidos en emociones "
               f"{'difíciles' if es_neg else 'agradables'}",
        evidencia={"dias": racha, "signo": s0},
        score=round(min(0.4 + racha * 0.1, 0.95), 2),
        urgencia=round(min(racha * 0.12, 0.9), 2) if es_neg else 0.2,
        ventana=f"últimos {racha} días",
        detectada_en=_ahora(),
    )


def detect_valence_trend(entries: list):
    """Compara la valencia media de los últimos 7 días vs los 7 previos."""
    now = datetime.utcnow().timestamp()
    rec, prev = [], []
    for e in entries:
        ts = _ts(e)
        if not ts:
            continue
        edad = (now - ts) / 86400
        if 0 <= edad < 7:
            rec.append(float(e.get("valencia") or 0))
        elif 7 <= edad < 14:
            prev.append(float(e.get("valencia") or 0))
    if len(rec) < 2 or len(prev) < 2:
        return None
    m_rec, m_prev = sum(rec) / len(rec), sum(prev) / len(prev)
    delta = m_rec - m_prev
    if abs(delta) < 0.25:
        return None
    mejora = delta > 0
    return Signal(
        tipo="tendencia_valencia",
        titulo="Tu ánimo viene mejorando esta semana" if mejora
               else "Tu ánimo viene bajando esta semana",
        evidencia={"valencia_reciente": round(m_rec, 2),
                   "valencia_previa": round(m_prev, 2), "delta": round(delta, 2)},
        score=round(min(0.4 + abs(delta), 0.9), 2),
        urgencia=round(min(abs(delta), 0.7), 2) if not mejora else 0.15,
        ventana="esta semana vs la anterior",
        detectada_en=_ahora(),
    )


def detect_recurring_trigger(entries: list):
    """Un mismo disparador aparece ≥3 veces en el historial."""
    freq: dict = {}
    for e in entries:
        d = (e.get("disparador") or "").strip().lower()
        if d:
            freq[d] = freq.get(d, 0) + 1
    if not freq:
        return None
    top, n = max(freq.items(), key=lambda kv: kv[1])
    if n < RECURRENCIA_MIN:
        return None
    return Signal(
        tipo="disparador_recurrente",
        titulo=f"«{top}» ha aparecido {n} veces como disparador",
        evidencia={"disparador": top, "veces": n},
        score=round(min(0.3 + n * 0.1, 0.85), 2),
        urgencia=0.3,
        ventana="historial",
        detectada_en=_ahora(),
    )


def detect_intensity_anomaly(entries: list):
    """La última entrada es mucho más intensa que el baseline reciente."""
    if len(entries) < 5:
        return None
    resto = [float(x.get("intensidad") or 0) for x in entries[1:21]]
    if len(resto) < 4:
        return None
    media = sum(resto) / len(resto)
    sd = (sum((x - media) ** 2 for x in resto) / len(resto)) ** 0.5
    i0 = float(entries[0].get("intensidad") or 0)
    if sd > 0 and i0 > media + 1.5 * sd:
        return Signal(
            tipo="intensidad_anomala",
            titulo=f"Tu última emoción fue más intensa de lo habitual ({int(i0)}/10)",
            evidencia={"intensidad": i0, "media": round(media, 1),
                       "desviacion": round(sd, 1)},
            score=0.6,
            urgencia=0.5,
            ventana="última entrada",
            detectada_en=_ahora(),
        )
    return None


def detect_logging_gap(entries: list):
    """Han pasado varios días sin registrar nada."""
    if not entries:
        return None
    dias = _dias_desde(entries[0])
    if dias >= 3:
        return Signal(
            tipo="ausencia_registro",
            titulo=f"Han pasado {dias} días desde tu último registro",
            evidencia={"dias_sin_registrar": dias},
            score=round(min(0.3 + dias * 0.05, 0.7), 2),
            urgencia=0.3,
            ventana="ahora",
            detectada_en=_ahora(),
        )
    return None


_DETECTORES = [
    detect_emocion_negativa_intensa,
    detect_streak,
    detect_valence_trend,
    detect_recurring_trigger,
    detect_intensity_anomaly,
    detect_logging_gap,
]


def compute_signals(entries: list) -> list:
    """Corre todos los detectores y devuelve las señales ordenadas por score."""
    signals = []
    for detector in _DETECTORES:
        try:
            s = detector(entries)
            if s:
                signals.append(s)
        except Exception:  # noqa: BLE001 - un detector roto no debe tumbar el resto
            continue
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def classify_state(signals: list) -> str:
    """Clasifica el estado emocional a partir de las señales detectadas.

    Devuelve: en_dificultad | volatil | en_mejora | desconectado | estable.
    """
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
