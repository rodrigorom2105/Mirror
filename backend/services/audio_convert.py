"""Conversión de audio a WAV 16 kHz mono mediante ffmpeg."""
import os
import subprocess
import tempfile
import wave

from services.audio_errors import AudioCorruptError

FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")


def to_wav16k_mono(input_path: str) -> tuple[str, float]:
    """Convierte un audio de cualquier formato a WAV PCM 16 kHz mono.

    Devuelve (ruta_del_wav, duración_en_segundos). El WAV se crea como archivo
    temporal; el llamador es responsable de borrarlo.
    Lanza AudioCorruptError si ffmpeg no puede decodificar el audio.
    """
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    cmd = [
        FFMPEG, "-nostdin", "-y", "-loglevel", "error",
        "-i", input_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise AudioCorruptError(
            f"ffmpeg no pudo decodificar el audio: {proc.stderr.strip()}"
        )
    try:
        duration = _wav_duration(out_path)
    except wave.Error as exc:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise AudioCorruptError(
            f"El WAV generado está corrupto: {exc}"
        ) from exc
    return out_path, duration


def _wav_duration(wav_path: str) -> float:
    """Duración en segundos de un WAV, leída de su cabecera."""
    with wave.open(wav_path, "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
    return frames / float(rate) if rate else 0.0
