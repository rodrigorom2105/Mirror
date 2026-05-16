CRISIS_KEYWORDS = [
    "suicidio", "suicidarme", "matarme", "quitarme la vida", "no quiero vivir",
    "autolesión", "cortarme", "hacerme daño", "lastimarme",
    "no vale la pena seguir", "mejor estaría muerto", "desaparecer para siempre",
    "ya no puedo más", "fin de todo", "terminar con todo",
]

def contains_crisis(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CRISIS_KEYWORDS)
