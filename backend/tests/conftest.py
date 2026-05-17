"""Fixtures de audio generados con ffmpeg (no se commitea ningún binario)."""
import os
import subprocess
import tempfile

import pytest


def _ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", *args], check=True
    )


@pytest.fixture(scope="session")
def tmp_audio_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture(scope="session")
def wav_2s(tmp_audio_dir):
    """WAV 16kHz mono de 2s (tono). Entrada ya convertida."""
    path = os.path.join(tmp_audio_dir, "tone.wav")
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", path)
    return path


@pytest.fixture(scope="session")
def webm_2s(tmp_audio_dir):
    """Audio webm/opus de 2s, como lo produce Chrome."""
    path = os.path.join(tmp_audio_dir, "clip.webm")
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:a", "libopus", path)
    return path


@pytest.fixture(scope="session")
def m4a_2s(tmp_audio_dir):
    """Audio mp4/aac de 2s, como lo produce Safari iOS."""
    path = os.path.join(tmp_audio_dir, "clip.m4a")
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:a", "aac", path)
    return path


@pytest.fixture(scope="session")
def webm_tiny(tmp_audio_dir):
    """Audio webm de 0.2s — más corto que el mínimo permitido."""
    path = os.path.join(tmp_audio_dir, "tiny.webm")
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.2",
            "-c:a", "libopus", path)
    return path


@pytest.fixture
def corrupt_audio(tmp_audio_dir):
    """Archivo con extensión de audio pero contenido basura."""
    path = os.path.join(tmp_audio_dir, "corrupt.webm")
    with open(path, "wb") as f:
        f.write(b"\x00\x01\x02 esto no es audio \xff\xfe")
    return path
