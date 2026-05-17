"""Selección del motor de transcripción según plataforma y configuración."""
import functools
import os
import platform

from services.audio_errors import EngineUnavailableError
from services.stt.base import Transcriber, TranscriptionResult  # noqa: F401
from services.stt.faster_whisper import FasterWhisperTranscriber
from services.stt.whisperkit import WhisperKitTranscriber


def _build_transcriber() -> Transcriber:
    engine = os.getenv("STT_ENGINE", "").strip().lower()
    if not engine:
        engine = "whisperkit" if platform.system() == "Darwin" else "faster_whisper"

    if engine == "whisperkit":
        return WhisperKitTranscriber(
            cli=os.getenv("WHISPERKIT_CLI", "whisperkit-cli"),
            model=os.getenv("WHISPERKIT_MODEL", "large-v3"),
            timeout=int(os.getenv("STT_TIMEOUT", "60")),
        )
    if engine == "faster_whisper":
        return FasterWhisperTranscriber(
            model_size=os.getenv("FASTER_WHISPER_MODEL", "small"),
        )
    # Subclase de AudioError para que el endpoint (Task 6) la mapee a HTTP
    # en vez de dejar escapar un 500 sin estructura.
    raise EngineUnavailableError(f"STT_ENGINE desconocido: {engine!r}")


@functools.lru_cache(maxsize=1)
def get_transcriber() -> Transcriber:
    """Devuelve el motor STT activo (singleton cacheado)."""
    return _build_transcriber()
