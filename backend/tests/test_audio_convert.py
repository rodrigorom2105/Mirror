import os
import wave

import pytest

from services.audio_convert import to_wav16k_mono
from services.audio_errors import AudioCorruptError


def test_converts_webm_to_wav_16k_mono(webm_2s):
    wav_path, duration = to_wav16k_mono(webm_2s)
    try:
        with wave.open(wav_path, "rb") as w:
            assert w.getframerate() == 16000
            assert w.getnchannels() == 1
        assert 1.8 < duration < 2.2
    finally:
        os.unlink(wav_path)


def test_converts_m4a_to_wav(m4a_2s):
    wav_path, duration = to_wav16k_mono(m4a_2s)
    try:
        with wave.open(wav_path, "rb") as w:
            assert w.getframerate() == 16000
            assert w.getnchannels() == 1
        assert 1.8 < duration < 2.2
    finally:
        os.unlink(wav_path)


def test_corrupt_audio_raises(corrupt_audio):
    with pytest.raises(AudioCorruptError):
        to_wav16k_mono(corrupt_audio)
