"""Detección de crisis con scoring y contexto.

Determinista a propósito: la seguridad no debe depender de un LLM lento que
puede fallar o alucinar. Mejora el matching binario anterior con:
- frases de ideación (peso alto) vs términos sueltos (peso medio),
- filtro de negación y de modismos (evita "matarme de risa"),
- corroboración con la señal RULER (emoción muy negativa e intensa).

Devuelve un nivel de 3 estados para que el frontend module la respuesta.
"""

# Frases inequívocas de ideación suicida — peso alto.
_FRASES_IDEACION = [
    "quitarme la vida", "no quiero vivir", "no quiero seguir viviendo",
    "quiero morir", "quiero morirme", "mejor estaria muerto",
    "mejor estaría muerto", "no vale la pena seguir", "no vale la pena vivir",
    "desaparecer para siempre", "terminar con todo", "acabar con todo",
    "no quiero despertar", "no quiero estar aqui", "no quiero estar aquí",
]

# Términos de autolesión/suicidio — peso medio; requieren no estar negados.
_TERMINOS = [
    "suicidio", "suicidarme", "matarme", "autolesion", "autolesión",
    "cortarme", "hacerme dano", "hacerme daño", "lastimarme",
]

# Frases ambiguas — peso bajo; suben de nivel solo con corroboración del RULER.
_AMBIGUAS = ["ya no puedo mas", "ya no puedo más", "no aguanto mas",
             "no aguanto más", "estoy harto de todo", "estoy harta de todo"]

# Modismos que contienen palabras de crisis pero NO lo son.
_MODISMOS = [
    "matarme de risa", "matar el tiempo", "matando el tiempo",
    "muerto de risa", "muerto de hambre", "muerto de sueno", "muerto de sueño",
    "muerto de cansancio", "me muero de hambre", "me muero de risa",
    "me muero de ganas", "me muero de frio", "me muero de frío",
]

_NEGADORES = {"no", "nunca", "jamas", "jamás", "tampoco", "ni"}


def _negado(text: str, term: str) -> bool:
    """True si hay un negador en las ~4 palabras previas al término."""
    idx = text.find(term)
    if idx < 0:
        return False
    previas = text[:idx].split()[-4:]
    return any(neg in previas for neg in _NEGADORES)


def assess_crisis(text: str, ruler: dict | None = None) -> dict:
    """Evalúa el riesgo de crisis. Devuelve {nivel, score, motivos}.

    nivel: "ninguno" | "vigilar" | "alto".
    """
    t = " " + (text or "").lower() + " "
    # Quita modismos antes de evaluar, para no contar falsos positivos.
    limpio = t
    for m in _MODISMOS:
        limpio = limpio.replace(m, " ")

    score = 0.0
    motivos: list[str] = []

    for frase in _FRASES_IDEACION:
        if frase in limpio:
            score += 0.6
            motivos.append(f"frase de ideación: «{frase}»")

    for term in _TERMINOS:
        if term in limpio and not _negado(limpio, term):
            score += 0.4
            motivos.append(f"término de riesgo: «{term}»")

    ambigua = False
    for frase in _AMBIGUAS:
        if frase in limpio:
            ambigua = True
            score += 0.15
            motivos.append(f"frase ambigua: «{frase}»")

    # Corroboración con el RULER: una sola fuente no basta para "alto".
    if ruler:
        try:
            val = float(ruler.get("valencia") or 0)
            inten = float(ruler.get("intensidad") or 0)
            if ruler.get("cuadrante") in ("rojo", "azul") and val <= -0.6 and inten >= 8:
                score += 0.2
                motivos.append("el RULER corrobora: emoción muy negativa e intensa")
        except (ValueError, TypeError):
            pass

    if score >= 0.6:
        nivel = "alto"
    elif score >= 0.3 or (score > 0 and ambigua):
        nivel = "vigilar"
    else:
        nivel = "ninguno"

    return {"nivel": nivel, "score": round(min(score, 1.0), 2), "motivos": motivos}


def contains_crisis(text: str) -> bool:
    """Compat: bool. True si el nivel detectado no es 'ninguno'."""
    return assess_crisis(text)["nivel"] != "ninguno"
