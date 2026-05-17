import pytest

import services.audio_pipeline as pipeline
from services.audio_errors import (
    AudioTooLongError,
    AudioTooShortError,
    EmptyTranscriptionError,
)
from services.stt.base import TranscriptionResult


class FakeTranscriber:
    name = "fake"

    def __init__(self, text):
        self._text = text

    def transcribe(self, wav_path):
        return TranscriptionResult(text=self._text)


def test_happy_path(monkeypatch, webm_2s):
    monkeypatch.setattr(
        pipeline, "get_transcriber", lambda: FakeTranscriber("hola mundo")
    )
    result = pipeline.transcribe_audio(webm_2s)
    assert result["text"] == "hola mundo"
    assert 1.8 < result["duration"] < 2.2


def test_too_short_raises(monkeypatch, webm_tiny):
    monkeypatch.setattr(
        pipeline, "get_transcriber", lambda: FakeTranscriber("x")
    )
    with pytest.raises(AudioTooShortError):
        pipeline.transcribe_audio(webm_tiny)


def test_too_long_raises(monkeypatch, webm_2s):
    monkeypatch.setattr(pipeline, "_MAX_DURATION", 1.0)
    monkeypatch.setattr(
        pipeline, "get_transcriber", lambda: FakeTranscriber("x")
    )
    with pytest.raises(AudioTooLongError):
        pipeline.transcribe_audio(webm_2s)


def test_empty_transcription_raises(monkeypatch, webm_2s):
    monkeypatch.setattr(
        pipeline, "get_transcriber", lambda: FakeTranscriber("   ")
    )
    with pytest.raises(EmptyTranscriptionError):
        pipeline.transcribe_audio(webm_2s)
