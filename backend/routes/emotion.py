from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
import tempfile, os
from logging_config import get_logger
from services.llm_service import extract_ruler
from services.memory_service import save_entry, set_feedback_reaction
from services.emotion_catalog import get_catalog
from services.entry_feedback import compute_intensity, generate_entry_feedback
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


def _analyze(full_text: str, emocion_seleccionada: str,
             client_time: str | None) -> dict:
    """Extrae RULER, calcula intensidad y genera el feedback. No guarda."""
    ruler = extract_ruler(full_text)
    ruler["emocion_seleccionada"] = emocion_seleccionada
    ruler["crisis_flag"] = contains_crisis(full_text)
    ruler["intensidad"] = compute_intensity(ruler, emocion_seleccionada)
    if client_time:
        ruler["client_time"] = client_time
    ruler["feedback"] = generate_entry_feedback(ruler, emocion_seleccionada,
                                                client_time)
    return ruler


class AnalyzeRequest(BaseModel):
    text: str
    emocion_seleccionada: str
    client_time: str | None = None


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    full_text = f"Emoción seleccionada: {req.emocion_seleccionada}. {req.text}"
    ruler = _analyze(full_text, req.emocion_seleccionada, req.client_time)
    ruler["transcripcion"] = req.text
    return ruler


@router.get("/emotions")
async def emotions():
    """Catálogo unificado de emociones — fuente única de la sub-matriz."""
    return get_catalog()


class ReactionRequest(BaseModel):
    entry_id: str
    reaccion: str


@router.post("/feedback/reaction")
async def feedback_reaction(req: ReactionRequest):
    """Registra si el feedback de la IA le ayudó al usuario."""
    return {"ok": set_feedback_reaction(req.entry_id, req.reaccion)}


@router.post("/save")
async def save(ruler: dict, background: BackgroundTasks):
    # El feedback y la reacción se aplanan a metadata escalar de ChromaDB.
    reaccion = ruler.pop("reaccion_feedback", None)
    fb = ruler.pop("feedback", None)
    fb = fb if isinstance(fb, dict) else {}  # tolera un payload malformado
    ruler["feedback_mensaje"] = fb.get("mensaje", "")
    ruler["feedback_modo"] = fb.get("modo", "")
    ruler["feedback_reaccion"] = reaccion or ""
    entry_id, saved_at = save_entry(ruler)
    ruler["saved_at"] = saved_at
    _update_profile(ruler, background)
    return {"id": entry_id, "saved_at": saved_at}


@router.post("/entry")
async def entry(
    audio: UploadFile = File(...),
    emocion_seleccionada: str = Form(...),
    client_time: str = Form(None),
):
    _log.info("Nueva entrada — emoción seleccionada: %s", emocion_seleccionada)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        data = await audio.read()
        tmp.write(data)
        tmp_path = tmp.name
    _log.debug("Audio recibido: %d bytes", len(data))
    try:
        # Import diferido: aísla el audio pipeline del arranque del módulo.
        from services.audio_pipeline import transcribe_audio

        transcription = transcribe_audio(tmp_path)
        full_text = f"Emoción seleccionada: {emocion_seleccionada}. {transcription['text']}"
        _log.info("Extrayendo RULER con el LLM…")
        ruler = _analyze(full_text, emocion_seleccionada, client_time)
        ruler["transcripcion"] = transcription["text"]
        if ruler["crisis_flag"]:
            _log.warning("crisis_flag activado en esta entrada")
        return ruler
    except AudioError as exc:
        _log.warning("Error de audio: %s", exc)
        raise HTTPException(exc.status_code, str(exc) or exc.detail)
    finally:
        os.unlink(tmp_path)
