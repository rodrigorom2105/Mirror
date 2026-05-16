"""Endpoint POST /api/transcribe — transcripción de voz a texto."""
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.audio_errors import AudioError
from services.audio_pipeline import transcribe_audio

router = APIRouter()

_MAX_SIZE_MB = int(os.getenv("AUDIO_MAX_SIZE_MB", "25"))
_MAX_SIZE_BYTES = _MAX_SIZE_MB * 1024 * 1024
_CHUNK_SIZE = 64 * 1024


class TranscribeResponse(BaseModel):
    text: str
    duration: float


async def _read_capped(audio: UploadFile) -> bytes:
    """Lee el archivo en bloques y aborta si supera el límite de tamaño.

    Evita bufferizar en memoria un cuerpo de request arbitrariamente grande
    (el endpoint escucha en la red local).
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await audio.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > _MAX_SIZE_BYTES:
            raise HTTPException(
                413, f"El audio supera el límite de {_MAX_SIZE_MB} MB."
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    content_type = audio.content_type or ""
    if not content_type.startswith("audio/"):
        raise HTTPException(400, "El archivo debe ser audio.")

    data = await _read_capped(audio)
    if not data:
        raise HTTPException(422, "El archivo de audio está vacío.")

    fd, tmp_path = tempfile.mkstemp(suffix=".audio")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(data)
        return transcribe_audio(tmp_path)
    except AudioError as exc:
        raise HTTPException(exc.status_code, str(exc) or exc.detail)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
