"""Catálogo de emociones — fuente única de la sub-matriz RULER.

Las 4 listas de 12 emociones (ordenadas de leve a intensa) son la base de:
- la sub-matriz del frontend (servida por GET /api/emotions),
- el cálculo de la intensidad emocional (posición -> intensidad, Task 2).
"""
import json
import os
import unicodedata

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "emotion_catalog.json")

with open(_PATH, encoding="utf-8") as _f:
    _CATALOG = json.load(_f)


def _norm(s: str) -> str:
    """Minúsculas y sin acentos, para emparejar nombres de emoción."""
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


# Índice nombre-normalizado -> posición 0-11 dentro de su cuadrante.
_POSITION = {}
for _q, _data in _CATALOG.items():
    for _i, _emo in enumerate(_data["emotions"]):
        _POSITION[_norm(_emo)] = _i


def get_catalog() -> dict:
    """El catálogo completo, tal cual, para servir al frontend."""
    return _CATALOG


def emotion_position(name: str) -> int | None:
    """Posición 0-11 de una emoción en su cuadrante, o None si no está."""
    return _POSITION.get(_norm(name))


def position_intensity(pos: int) -> float:
    """Mapea una posición 0-11 a una intensidad 1.0-10.0."""
    return 1.0 + pos * (9.0 / 11.0)
