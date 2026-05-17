from fastapi import APIRouter, Query

from services.memory_service import compute_patterns, get_history
from services.signals_engine import compute_signals

router = APIRouter()


@router.get("/history")
async def history(limit: int = Query(20, ge=1, le=100)):
    entries = get_history(limit=limit)
    return {"entries": entries, "total": len(entries)}


@router.get("/patterns")
async def patterns():
    """Patrones: histograma básico + insights reales del motor de señales."""
    base = compute_patterns()
    entries = get_history(limit=100)
    signals = compute_signals(entries)

    base["insights"] = [
        {"tipo": s.tipo, "texto": s.titulo, "score": s.score}
        for s in signals
    ]
    try:
        from services.profile_service import get_profile
        from services.reasoning_pipeline import classify_state
        base["racha_registro"] = get_profile().get("registro", {}).get("racha_dias", 0)
        base["estado_actual"] = classify_state(signals) if signals else "sin_datos"
    except Exception:  # noqa: BLE001
        base["racha_registro"] = 0
        base["estado_actual"] = "sin_datos"
    return base
