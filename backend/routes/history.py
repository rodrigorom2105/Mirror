from fastapi import APIRouter, Query
from services.memory_service import get_history, compute_patterns

router = APIRouter()

@router.get("/history")
async def history(limit: int = Query(20, ge=1, le=100)):
    entries = get_history(limit=limit)
    return {"entries": entries, "total": len(entries)}

@router.get("/patterns")
async def patterns():
    return compute_patterns()
