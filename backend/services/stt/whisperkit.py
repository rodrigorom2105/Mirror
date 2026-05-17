"""Motor STT primario: WhisperKit, vía el binario whisperkit-cli."""
import subprocess

from services.audio_errors import (
    EngineUnavailableError,
    TranscriptionFailedError,
    TranscriptionTimeout,
)
from services.stt.base import TranscriptionResult

_FAILED_MARKER = "Transcription failed"


class WhisperKitTranscriber:
    """Transcriptor que ejecuta `whisperkit-cli transcribe` como subproceso.

    En modo no-verbose, whisperkit-cli imprime únicamente el texto transcrito
    a stdout, o "Transcription failed" si falló.
    """

    name = "whisperkit"

    def __init__(self, cli: str, model: str, timeout: int, model_path: str = ""):
        self._cli = cli
        self._model = model
        self._timeout = timeout
        self._model_path = model_path

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        cmd = [
            self._cli, "transcribe",
            "--audio-path", wav_path,
            "--language", "es",
        ]
        if self._model_path:
            cmd += ["--model-path", self._model_path]
        else:
            cmd += ["--model", self._model]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout
            )
        except subprocess.TimeoutExpired:
            raise TranscriptionTimeout(
                f"whisperkit-cli excedió {self._timeout}s"
            )
        except FileNotFoundError:
            raise EngineUnavailableError(
                f"No se encontró el binario '{self._cli}'. "
                "Instálalo con: brew install whisperkit-cli"
            )
        if proc.returncode != 0:
            raise TranscriptionFailedError(
                f"whisperkit-cli salió con código {proc.returncode}: "
                f"{proc.stderr.strip()}"
            )
        text = proc.stdout.strip()
        if not text or text == _FAILED_MARKER:
            raise TranscriptionFailedError(
                "whisperkit-cli no devolvió transcripción"
            )
        return TranscriptionResult(text=text)
