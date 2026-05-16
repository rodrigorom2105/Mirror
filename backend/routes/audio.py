"""Endpoint POST /api/transcribe — implementación en progreso (ver plan Task 6)."""
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    raise HTTPException(503, "El audio pipeline aún no está disponible.")
