"""Motor STT de respaldo: faster-whisper (en proceso, multiplataforma).

Dependencia OPCIONAL: faster-whisper no se instala por defecto. El import es
perezoso para que la ausencia del paquete no rompa el resto del backend.
"""
from services.audio_errors import EngineUnavailableError, TranscriptionFailedError
from services.stt.base import TranscriptionResult


class FasterWhisperTranscriber:
    """Transcriptor de respaldo basado en faster-whisper."""

    name = "faster-whisper"

    def __init__(self, model_size: str):
        self._model_size = model_size
        self._model = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise EngineUnavailableError(
                "faster-whisper no está instalado. "
                "Instálalo con: pip install faster-whisper"
            )
        self._model = WhisperModel(
            self._model_size, device="cpu", compute_type="int8"
        )

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        self._ensure_model()
        try:
            segments, _info = self._model.transcribe(wav_path, language="es")
            text = " ".join(seg.text for seg in segments).strip()
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionFailedError(f"faster-whisper falló: {exc}")
        return TranscriptionResult(text=text)
