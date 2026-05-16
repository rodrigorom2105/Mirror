from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import tempfile, os
from services.llm_service import extract_ruler
from services.memory_service import save_entry
from crisis_keywords import contains_crisis

router = APIRouter()

class AnalyzeRequest(BaseModel):
    text: str

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    ruler = extract_ruler(req.text)
    ruler["crisis_flag"] = contains_crisis(req.text)
    return ruler

@router.post("/save")
async def save(ruler: dict):
    entry_id = save_entry(ruler)
    return {"id": entry_id, "saved": True}

@router.post("/entry")
async def entry(
    audio: UploadFile = File(...),
    emocion_seleccionada: str = Form(...),
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        # Import diferido: el audio pipeline (services.audio_pipeline) se
        # construye en la Task 6 del plan; importarlo aquí dentro evita
        # romper `import main` mientras tanto.
        from services.audio_pipeline import transcribe_audio

        transcription = transcribe_audio(tmp_path)
        full_text = f"Emoción seleccionada: {emocion_seleccionada}. {transcription['text']}"
        ruler = extract_ruler(full_text)
        ruler["emocion_seleccionada"] = emocion_seleccionada
        ruler["transcripcion"] = transcription["text"]
        ruler["crisis_flag"] = contains_crisis(full_text)
        entry_id = save_entry(ruler)
        return {**ruler, "id": entry_id}
    finally:
        os.unlink(tmp_path)
