"""Contrato común de los motores de transcripción (STT)."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class TranscriptionResult:
    """Resultado de transcribir un audio."""

    text: str


@runtime_checkable
class Transcriber(Protocol):
    """Un motor de transcripción.

    Implementaciones: WhisperKitTranscriber, FasterWhisperTranscriber.
    """

    name: str

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        """Transcribe un WAV 16 kHz mono y devuelve el texto."""
        ...
