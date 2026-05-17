import subprocess

import pytest

from services.audio_errors import (
    EngineUnavailableError,
    TranscriptionFailedError,
    TranscriptionTimeout,
)
from services.stt.base import TranscriptionResult
from services.stt.whisperkit import WhisperKitTranscriber


def _transcriber():
    return WhisperKitTranscriber(cli="whisperkit-cli", model="large-v3", timeout=60)


def test_returns_stdout_as_text(monkeypatch):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(
            cmd, 0, stdout="hola, me siento bien\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _transcriber().transcribe("x.wav")
    assert isinstance(result, TranscriptionResult)
    assert result.text == "hola, me siento bien"


def test_nonzero_exit_raises(monkeypatch):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(TranscriptionFailedError):
        _transcriber().transcribe("x.wav")


def test_failed_marker_raises(monkeypatch):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(
            cmd, 0, stdout="Transcription failed\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(TranscriptionFailedError):
        _transcriber().transcribe("x.wav")


def test_empty_output_raises(monkeypatch):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="   \n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(TranscriptionFailedError):
        _transcriber().transcribe("x.wav")


def test_timeout_raises(monkeypatch):
    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 60)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(TranscriptionTimeout):
        _transcriber().transcribe("x.wav")


def test_missing_binary_raises(monkeypatch):
    def fake_run(cmd, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(EngineUnavailableError):
        _transcriber().transcribe("x.wav")
