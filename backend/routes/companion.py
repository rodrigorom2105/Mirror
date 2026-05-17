"""Endpoints de acompañamiento contextual.

/api/companion → corre el pipeline de razonamiento (trigger on_open). Devuelve
                 un acompañamiento o `intervenir: false` si no hay nada que decir.
/api/signals   → las señales detectadas, crudas y con score. Sin LLM, instantáneo.
"""
from fastapi import APIRouter

from services.memory_service import get_history
from services.reasoning_pipeline import run_companion_pipeline
from services.signals_engine import compute_signals

router = APIRouter()


@router.get("/companion")
async def companion():
    """Acompañamiento contextual al abrir la app."""
    result = run_companion_pipeline(trigger="on_open")
    return result.to_dict()


@router.get("/signals")
async def signals():
    """Señales detectadas en el historial — para la vista de patrones."""
    entries = get_history(limit=100)
    sigs = compute_signals(entries)
    return {"signals": [s.to_dict() for s in sigs], "total": len(sigs)}
