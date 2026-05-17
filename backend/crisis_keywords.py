"""Compat: la lógica de crisis vive ahora en services/crisis_detector.py.

Este módulo se conserva para no romper los imports existentes
(`from crisis_keywords import contains_crisis`). Reexporta el detector nuevo,
que añade scoring, niveles, filtro de negación y de modismos.
"""
from services.crisis_detector import assess_crisis, contains_crisis  # noqa: F401
