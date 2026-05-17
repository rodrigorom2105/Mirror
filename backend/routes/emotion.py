from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import tempfile, os
from logging_config import get_logger
from services.llm_service import extract_ruler
from services.memory_service import save_entry
from services.audio_errors import AudioError
from crisis_keywords import contains_crisis

router = APIRouter()
_log = get_logger("entry")

class AnalyzeRequest(BaseModel):
    text: str

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    ruler = extract_ruler(req.text)
    ruler["crisis_flag"] = contains_crisis(req.text)
    return ruler

@router.post("/save")
async def save(ruler: dict):
    entry_id, saved_at = save_entry(ruler)
    return {"id": entry_id, "saved_at": saved_at}

@router.post("/entry")
async def entry(
    audio: UploadFile = File(...),
    emocion_seleccionada: str = Form(...),
):
    _log.info("Nueva entrada — emoción seleccionada: %s", emocion_seleccionada)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        data = await audio.read()
        tmp.write(data)
        tmp_path = tmp.name
    _log.debug("Audio recibido: %d bytes", len(data))
    try:
        # Import diferido: el audio pipeline (services.audio_pipeline) se
        # construye en la Task 6 del plan; importarlo aquí dentro evita
        # romper `import main` mientras tanto.
        from services.audio_pipeline import transcribe_audio

        transcription = transcribe_audio(tmp_path)
        full_text = f"Emoción seleccionada: {emocion_seleccionada}. {transcription['text']}"
        _log.info("Extrayendo RULER con el LLM…")
        ruler = extract_ruler(full_text)
        ruler["emocion_seleccionada"] = emocion_seleccionada
        ruler["transcripcion"] = transcription["text"]
        ruler["crisis_flag"] = contains_crisis(full_text)
        if ruler["crisis_flag"]:
            _log.warning("crisis_flag activado en esta entrada")
        entry_id, _ = save_entry(ruler)
        _log.info("Entrada guardada — id=%s", entry_id)
        return {**ruler, "id": entry_id}
    except AudioError as exc:
        _log.warning("Error de audio: %s", exc)
        # Errores esperados del audio pipeline (audio corto, sin voz, formato
        # inválido): se mapean a su código HTTP en vez de escapar como un 500
        # sin estructura que el frontend no puede parsear.
        raise HTTPException(exc.status_code, str(exc) or exc.detail)
    finally:
        os.unlink(tmp_path)
