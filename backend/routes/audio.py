from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import tempfile, os
from services.whisper_service import transcribe_audio

router = APIRouter()

class TranscribeResponse(BaseModel):
    text: str
    duration: float

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(400, "File must be audio")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        result = transcribe_audio(tmp_path)
        return result
    finally:
        os.unlink(tmp_path)
