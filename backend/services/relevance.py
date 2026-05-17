"""Scoring de relevancia del contexto recuperado.

`memory_service.retrieve_relevant` ya puntúa cada entrada (similitud +
recencia + intensidad) y la devuelve con `_score`. Aquí se filtra ese
contexto: descartar lo poco relevante antes de mandarlo al LLM significa
prompts más cortos, respuestas más rápidas y menos ruido.
"""
import os

_MIN_SOURCE_SCORE = float(os.getenv("RELEVANCE_MIN_SOURCE_SCORE", "0.35"))


def filter_relevant_sources(sources: list, min_score: float | None = None) -> list:
    """Descarta sources por debajo del umbral de relevancia.

    Nunca devuelve vacío si había sources: deja al menos los 2 mejores, para
    que el LLM no se quede sin ningún contexto.
    """
    floor = _MIN_SOURCE_SCORE if min_score is None else min_score
    relevantes = [s for s in sources if s.get("_score", 1.0) >= floor]
    if relevantes:
        return relevantes
    return sources[:2]
