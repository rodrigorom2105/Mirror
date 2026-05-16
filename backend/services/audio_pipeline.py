"""Orquestación del audio pipeline: audio crudo -> texto transcrito."""
import os

from services.audio_convert import to_wav16k_mono
from services.audio_errors import (
    AudioTooLongError,
    AudioTooShortError,
    EmptyTranscriptionError,
)
from services.stt import get_transcriber

_MIN_DURATION = float(os.getenv("AUDIO_MIN_DURATION", "0.5"))
_MAX_DURATION = float(os.getenv("AUDIO_MAX_DURATION", "120"))


def transcribe_audio(audio_path: str) -> dict:
    """Convierte y transcribe un archivo de audio.

    Devuelve {"text": str, "duration": float}.
    Lanza subclases de AudioError ante audio inválido o fallo de transcripción.
    """
    wav_path, duration = to_wav16k_mono(audio_path)
    try:
        if duration < _MIN_DURATION:
            raise AudioTooShortError(
                f"El audio dura {duration:.2f}s (mínimo {_MIN_DURATION}s)."
            )
        if duration > _MAX_DURATION:
            raise AudioTooLongError(
                f"El audio dura {duration:.0f}s (máximo {_MAX_DURATION:.0f}s)."
            )
        result = get_transcriber().transcribe(wav_path)
        text = result.text.strip()
        if not text:
            raise EmptyTranscriptionError()
        return {"text": text, "duration": round(duration, 2)}
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)
