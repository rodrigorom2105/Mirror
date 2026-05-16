"""Test de integración: WhisperKit transcribiendo voz real en español.

Se salta en la suite rápida. Correr con:  pytest -m integration
Requiere: whisperkit-cli instalado y macOS (`say`). La primera corrida
descarga el modelo (lento, una sola vez).
"""
import os
import subprocess
import tempfile

import pytest

from services.stt.whisperkit import WhisperKitTranscriber
from services.audio_convert import to_wav16k_mono

pytestmark = pytest.mark.integration


@pytest.fixture
def spanish_wav():
    fd, aiff = tempfile.mkstemp(suffix=".aiff")
    os.close(fd)
    subprocess.run(
        ["say", "-o", aiff,
         "hola, hoy me siento un poco abrumado por el trabajo"],
        check=True,
    )
    wav_path, _duration = to_wav16k_mono(aiff)
    yield wav_path
    for p in (aiff, wav_path):
        if os.path.exists(p):
            os.unlink(p)


def test_whisperkit_transcribes_spanish(spanish_wav):
    transcriber = WhisperKitTranscriber(
        cli="whisperkit-cli", model="large-v3", timeout=300
    )
    result = transcriber.transcribe(spanish_wav)
    text = result.text.lower()
    assert "trabajo" in text or "abrumado" in text
