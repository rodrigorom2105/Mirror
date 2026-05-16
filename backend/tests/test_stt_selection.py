import pytest

import services.stt as stt
from services.audio_errors import EngineUnavailableError
from services.stt.faster_whisper import FasterWhisperTranscriber
from services.stt.whisperkit import WhisperKitTranscriber


def test_selects_whisperkit_on_macos(monkeypatch):
    stt.get_transcriber.cache_clear()
    monkeypatch.delenv("STT_ENGINE", raising=False)
    monkeypatch.setattr("services.stt.platform.system", lambda: "Darwin")
    assert isinstance(stt.get_transcriber(), WhisperKitTranscriber)
    stt.get_transcriber.cache_clear()


def test_selects_fallback_on_linux(monkeypatch):
    stt.get_transcriber.cache_clear()
    monkeypatch.delenv("STT_ENGINE", raising=False)
    monkeypatch.setattr("services.stt.platform.system", lambda: "Linux")
    assert isinstance(stt.get_transcriber(), FasterWhisperTranscriber)
    stt.get_transcriber.cache_clear()


def test_env_var_overrides_platform(monkeypatch):
    stt.get_transcriber.cache_clear()
    monkeypatch.setenv("STT_ENGINE", "faster_whisper")
    monkeypatch.setattr("services.stt.platform.system", lambda: "Darwin")
    assert isinstance(stt.get_transcriber(), FasterWhisperTranscriber)
    stt.get_transcriber.cache_clear()


def test_unknown_engine_raises_audio_error(monkeypatch):
    stt.get_transcriber.cache_clear()
    monkeypatch.setenv("STT_ENGINE", "deepgram")
    with pytest.raises(EngineUnavailableError):
        stt.get_transcriber()
    stt.get_transcriber.cache_clear()
