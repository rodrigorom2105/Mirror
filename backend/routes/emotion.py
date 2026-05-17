from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
import tempfile, os
from logging_config import get_logger
from services.llm_service import extract_ruler
from services.memory_service import save_entry
from services.audio_errors import AudioError
from crisis_keywords import contains_crisis

router = APIRouter()
_log = get_logger("entry")


def _update_profile(ruler: dict, background: BackgroundTasks) -> None:
    """Integra la entrada en el perfil consolidado. Nunca rompe el guardado."""
    try:
        from services.profile_service import (
            regenerate_narrative,
            should_regenerate_narrative,
            update_profile_with_entry,
        )
        p = update_profile_with_entry(ruler)
        if should_regenerate_narrative(p):
            background.add_task(regenerate_narrative)
    except Exception as exc:  # noqa: BLE001 - el perfil es un derivado, no crítico
        _log.warning("No se pudo actualizar el perfil: %s", exc)


def _acompanamiento_post_entry():
    """Corre el pipeline de razonamiento tras guardar. Devuelve dict o None.

    El pipeline decide por sí mismo si vale la pena intervenir; aquí solo se
    expone el resultado cuando interviene.
    """
    try:
        from services.reasoning_pipeline import run_companion_pipeline
        result = run_companion_pipeline(trigger="post_entry")
        return result.to_dict() if result.intervenir else None
    except Exception as exc:  # noqa: BLE001 - el acompañamiento nunca rompe el guardado
        _log.warning("Pipeline de acompañamiento falló: %s", exc)
        return None

class AnalyzeRequest(BaseModel):
    text: str

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    ruler = extract_ruler(req.text)
    ruler["crisis_flag"] = contains_crisis(req.text)
    return ruler

@router.post("/save")
async def save(ruler: dict, background: BackgroundTasks):
    entry_id, saved_at = save_entry(ruler)
    ruler["saved_at"] = saved_at
    _update_profile(ruler, background)
    acompanamiento = _acompanamiento_post_entry()
    return {"id": entry_id, "saved_at": saved_at, "acompanamiento": acompanamiento}

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
        return ruler
    except AudioError as exc:
        _log.warning("Error de audio: %s", exc)
        # Errores esperados del audio pipeline (audio corto, sin voz, formato
        # inválido): se mapean a su código HTTP en vez de escapar como un 500
        # sin estructura que el frontend no puede parsear.
        raise HTTPException(exc.status_code, str(exc) or exc.detail)
    finally:
        os.unlink(tmp_path)
