"""Orquestación del audio pipeline: audio crudo -> texto transcrito."""
import os
import subprocess
import tempfile
import time

from logging_config import get_logger
from services.audio_convert import FFMPEG, to_wav16k_mono
from services.audio_errors import (
    AudioTooLongError,
    AudioTooShortError,
    EmptyTranscriptionError,
    TranscriptionFailedError,
)
from services.stt import get_transcriber

_log = get_logger("audio")

_MIN_DURATION = float(os.getenv("AUDIO_MIN_DURATION", "0.5"))
_MAX_DURATION = float(os.getenv("AUDIO_MAX_DURATION", "120"))


def transcribe_audio(audio_path: str) -> dict:
    """Convierte y transcribe un archivo de audio.

    Devuelve {"text": str, "duration": float}.
    Lanza subclases de AudioError ante audio inválido o fallo de transcripción.
    """
    wav_path, duration = to_wav16k_mono(audio_path)
    _log.info("Audio convertido a WAV 16 kHz mono — %.2fs", duration)
    try:
        if duration < _MIN_DURATION:
            raise AudioTooShortError(
                f"El audio dura {duration:.2f}s (mínimo {_MIN_DURATION}s)."
            )
        if duration > _MAX_DURATION:
            raise AudioTooLongError(
                f"El audio dura {duration:.0f}s (máximo {_MAX_DURATION:.0f}s)."
            )
        transcriber = get_transcriber()
        _log.info("Transcribiendo con %s…", transcriber.name)
        started = time.perf_counter()
        result = transcriber.transcribe(wav_path)
        text = result.text.strip()
        if not text:
            raise EmptyTranscriptionError()
        _log.info(
            "Transcripción lista en %.1fs: %r",
            time.perf_counter() - started, text,
        )
        return {"text": text, "duration": round(duration, 2)}
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


def warmup() -> None:
    """Precarga el modelo STT para evitar el cold start en la primera petición.

    La primera carga del modelo en CoreML es lenta (decenas de segundos);
    transcribir aquí un WAV de silencio paga ese costo en el arranque del
    server y no en la primera grabación real del usuario.
    """
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    _log.info("Precargando el modelo STT (warm-up)…")
    try:
        subprocess.run(
            [
                FFMPEG, "-nostdin", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                "-t", "1", "-c:a", "pcm_s16le", wav_path,
            ],
            check=True,
            capture_output=True,
        )
        try:
            get_transcriber().transcribe(wav_path)
        except TranscriptionFailedError:
            # El silencio puede no producir texto; da igual: el objetivo es
            # dejar el modelo cargado, y para eso ya se ejecutó el motor.
            pass
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)
