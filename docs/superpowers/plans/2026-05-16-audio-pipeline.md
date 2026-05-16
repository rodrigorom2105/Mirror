# Audio Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el backend de transcripción de voz de Mirror: audio del navegador → texto en español, vía un motor STT multi-backend (WhisperKit en Mac) expuesto en `POST /api/transcribe`.

**Architecture:** Capa de servicios en `backend/services/` con una abstracción `Transcriber` (Protocol) que aísla el motor STT. El motor primario es WhisperKit, invocado como subproceso `whisperkit-cli`; hay un fallback opcional `faster-whisper`. Un servicio de conversión usa `ffmpeg` para normalizar cualquier audio a WAV 16 kHz mono. `audio_pipeline.transcribe_audio()` orquesta convertir → validar → transcribir → validar, y el endpoint mapea errores a códigos HTTP.

**Tech Stack:** Python 3.13, FastAPI, `ffmpeg` (subproceso), `whisperkit-cli` (subproceso), `faster-whisper` (opcional), `pytest`. Control de versiones con **GitButler** (`but`).

---

## Convenciones para todo el plan

- **Directorio de trabajo:** todos los comandos se ejecutan desde `backend/` con el venv activado (`source .venv/bin/activate`), salvo que se indique otra cosa.
- **Commits:** se usa GitButler. Hay una sola branch aplicada (`feat/audio-pipeline`), así que `but commit -m "..."` commitea todos los cambios sin asignar a esa branch. Cada Task termina en exactamente un commit = un milestone.
- **Tests:** `pytest` corre la suite rápida (excluye `integration` por config). El test real de WhisperKit se corre aparte con `pytest -m integration`.
- **No se toca `frontend/app.js`** ni `routes/{emotion,history,chat}.py` ni `main.py`.

---

## Task 1: Setup — entorno, dependencias, config y andamiaje

Crea el entorno aislado, las excepciones del pipeline, la infraestructura de tests
y deja la app importable (elimina el stub viejo de whisper.cpp).

**Files:**
- Create: `backend/.venv/` (entorno virtual, no se commitea)
- Modify: `backend/requirements.txt`
- Modify: `.env.example`  (en la raíz del repo, no dentro de `backend/`)
- Create: `backend/services/audio_errors.py`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Replace: `backend/routes/audio.py`  (stub temporal hasta Task 6)
- Delete: `backend/services/whisper_service.py`

- [ ] **Step 1: Crear el venv con Python 3.13 e instalar dependencias**

Desde `backend/`:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python --version   # debe imprimir Python 3.13.x
```

- [ ] **Step 2: Reescribir `backend/requirements.txt`**

Contenido completo (quita `pydub`, agrega `pytest`). Versiones compatibles con
Python 3.13 — los pins originales del proyecto (`pydantic==2.7.0`, etc.) no
construyen en 3.13:

```
fastapi==0.136.1
uvicorn[standard]==0.47.0
python-multipart==0.0.9
pydantic==2.10.0
httpx==0.28.1
chromadb==0.5.0
python-dotenv==1.2.2

# Tests (dev)
pytest==8.3.4

# Fallback STT opcional — descomentar SOLO si se necesita el motor de respaldo.
# faster-whisper==1.1.0
```

Luego instalar:

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Reescribir el `.env.example` de la raíz del repo**

Archivo `.env.example` (en la raíz del repo, no en `backend/`). Contenido completo:

```
OLLAMA_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b-instruct
EMBED_MODEL=nomic-embed-text
CHROMA_PATH=./data/chroma_db

# --- Audio pipeline (STT) ---
STT_ENGINE=whisperkit
WHISPERKIT_CLI=whisperkit-cli
WHISPERKIT_MODEL=large-v3
FASTER_WHISPER_MODEL=small
STT_TIMEOUT=60
AUDIO_MIN_DURATION=0.5
AUDIO_MAX_DURATION=120
AUDIO_MAX_SIZE_MB=25
```

- [ ] **Step 4: Crear `backend/services/audio_errors.py`**

```python
"""Excepciones del audio pipeline.

Cada excepción lleva el código HTTP que le corresponde, para que el endpoint
las mapee de forma genérica. `detail` es el mensaje por defecto si la excepción
se levanta sin argumentos.
"""


class AudioError(Exception):
    """Base de todos los errores del audio pipeline."""

    status_code = 500
    detail = "Error procesando el audio."


class AudioCorruptError(AudioError):
    status_code = 422
    detail = "El audio está corrupto o en un formato no soportado."


class AudioTooShortError(AudioError):
    status_code = 422
    detail = "El audio es demasiado corto."


class AudioTooLongError(AudioError):
    status_code = 422
    detail = "El audio es demasiado largo."


class EmptyTranscriptionError(AudioError):
    status_code = 422
    detail = "No se detectó voz en el audio."


class TranscriptionTimeout(AudioError):
    status_code = 504
    detail = "La transcripción tardó demasiado."


class TranscriptionFailedError(AudioError):
    status_code = 500
    detail = "Falló la transcripción del audio."


class EngineUnavailableError(AudioError):
    status_code = 503
    detail = "El motor de transcripción no está disponible."
```

- [ ] **Step 5: Crear `backend/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
markers =
    integration: prueba que corre el motor STT real (lenta; requiere whisperkit-cli)
addopts = -m "not integration"
```

- [ ] **Step 6: Crear `backend/tests/conftest.py`**

Genera todos los audios de prueba con `ffmpeg` en tiempo de test — no se commitea
ningún binario.

```python
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
```

- [ ] **Step 7: Reemplazar `backend/routes/audio.py` con un stub temporal**

El endpoint real se implementa en la Task 6. Este stub mantiene `main.py`
importable y la app arrancable mientras tanto (no depende de `whisper_service`,
que se borra en el siguiente step).

```python
"""Endpoint POST /api/transcribe — implementación en progreso (ver plan Task 6)."""
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    raise HTTPException(503, "El audio pipeline aún no está disponible.")
```

- [ ] **Step 8: Borrar el stub viejo `backend/services/whisper_service.py`**

```bash
rm services/whisper_service.py
```

- [ ] **Step 9: Verificar que la app sigue importable**

```bash
python -c "import routes.audio; import services.audio_errors; print('OK')"
```
Expected: imprime `OK` sin errores.

- [ ] **Step 10: Commit (milestone 1)**

```bash
but commit -m "chore(audio): scaffold STT structure, venv and config

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Servicio de conversión de audio (`audio_convert.py`)

Convierte cualquier formato de audio a WAV 16 kHz mono con `ffmpeg` y reporta la
duración.

**Files:**
- Create: `backend/services/audio_convert.py`
- Test: `backend/tests/test_audio_convert.py`

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_audio_convert.py`:

```python
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
        assert os.path.exists(wav_path)
        assert duration > 1.0
    finally:
        os.unlink(wav_path)


def test_corrupt_audio_raises(corrupt_audio):
    with pytest.raises(AudioCorruptError):
        to_wav16k_mono(corrupt_audio)
```

- [ ] **Step 2: Correr el test para verificar que falla**

```bash
pytest tests/test_audio_convert.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services.audio_convert'`.

- [ ] **Step 3: Implementar `backend/services/audio_convert.py`**

```python
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
    return out_path, _wav_duration(out_path)


def _wav_duration(wav_path: str) -> float:
    """Duración en segundos de un WAV, leída de su cabecera."""
    with wave.open(wav_path, "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
    return frames / float(rate) if rate else 0.0
```

- [ ] **Step 4: Correr el test para verificar que pasa**

```bash
pytest tests/test_audio_convert.py -v
```
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit (milestone 2)**

```bash
but commit -m "feat(audio): add ffmpeg conversion service

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Abstracción `Transcriber` (`stt/base.py`)

Define el contrato común que cualquier motor STT debe cumplir. La lógica de
selección de motor (`get_transcriber()`) se implementa en la Task 5, una vez que
ambos motores existen — así cada commit deja el árbol verde.

**Files:**
- Create: `backend/services/stt/__init__.py`  (marcador de paquete, vacío)
- Create: `backend/services/stt/base.py`
- Test: `backend/tests/test_stt_base.py`

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_stt_base.py`:

```python
from services.stt.base import Transcriber, TranscriptionResult


def test_transcription_result_holds_text():
    assert TranscriptionResult(text="hola mundo").text == "hola mundo"


def test_transcriber_protocol_is_runtime_checkable():
    class Dummy:
        name = "dummy"

        def transcribe(self, wav_path):
            return TranscriptionResult(text="x")

    assert isinstance(Dummy(), Transcriber)


def test_incomplete_class_is_not_a_transcriber():
    class NotATranscriber:
        name = "x"

    assert not isinstance(NotATranscriber(), Transcriber)
```

- [ ] **Step 2: Correr el test para verificar que falla**

```bash
pytest tests/test_stt_base.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services.stt'`.

- [ ] **Step 3: Crear el paquete `backend/services/stt/`**

Crear el archivo vacío `backend/services/stt/__init__.py`:

```python
"""Paquete de motores de transcripción (STT)."""
```

- [ ] **Step 4: Implementar `backend/services/stt/base.py`**

```python
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
```

- [ ] **Step 5: Correr el test para verificar que pasa**

```bash
pytest tests/test_stt_base.py -v
```
Expected: PASS — 3 tests.

- [ ] **Step 6: Commit (milestone 3)**

```bash
but commit -m "feat(audio): add Transcriber abstraction

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Motor primario WhisperKit (`stt/whisperkit.py`)

Implementa `Transcriber` ejecutando `whisperkit-cli` como subproceso. Incluye el
test de integración real (marcado `integration`, se corre aparte).

**Files:**
- Create: `backend/services/stt/whisperkit.py`
- Test: `backend/tests/test_stt_whisperkit.py`
- Test: `backend/tests/test_integration_whisperkit.py`

**Contexto del CLI (verificado en el repo de WhisperKit):** en modo no-verbose,
`whisperkit-cli transcribe` imprime a **stdout únicamente el texto transcrito**
(`print(result.text)`), o la cadena literal `Transcription failed` si falla.

- [ ] **Step 1: Instalar `whisperkit-cli` y confirmar su interfaz**

```bash
brew install whisperkit-cli
whisperkit-cli transcribe --help
```
Expected: el help lista las flags `--audio-path`, `--model`, `--language`.
Si algún nombre de flag difiere, ajustar el comando en el Step 3 acorde.

- [ ] **Step 2: Escribir el test que falla (subproceso mockeado)**

`backend/tests/test_stt_whisperkit.py`:

```python
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
```

- [ ] **Step 3: Correr el test para verificar que falla**

```bash
pytest tests/test_stt_whisperkit.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services.stt.whisperkit'`.

- [ ] **Step 4: Implementar `backend/services/stt/whisperkit.py`**

```python
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

    def __init__(self, cli: str, model: str, timeout: int):
        self._cli = cli
        self._model = model
        self._timeout = timeout

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        cmd = [
            self._cli, "transcribe",
            "--audio-path", wav_path,
            "--model", self._model,
            "--language", "es",
        ]
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
```

- [ ] **Step 5: Correr el test unitario para verificar que pasa**

```bash
pytest tests/test_stt_whisperkit.py -v
```
Expected: PASS — 6 tests.

- [ ] **Step 6: Escribir el test de integración real**

`backend/tests/test_integration_whisperkit.py` — usa el TTS de macOS (`say`)
para generar voz real en español y la transcribe con WhisperKit de verdad.

```python
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
        cli="whisperkit-cli", model="large-v3", timeout=120
    )
    result = transcriber.transcribe(spanish_wav)
    text = result.text.lower()
    assert "trabajo" in text or "abrumado" in text
```

- [ ] **Step 7: Correr el test de integración**

```bash
pytest -m integration tests/test_integration_whisperkit.py -v -s
```
Expected: PASS. La primera corrida descarga el modelo `large-v3` (puede tardar
varios minutos); las siguientes son rápidas.

- [ ] **Step 8: Confirmar que la suite rápida sigue verde**

```bash
pytest -v
```
Expected: PASS; el test de integración aparece como `deselected`.

- [ ] **Step 9: Commit (milestone 4)**

```bash
but commit -m "feat(audio): add WhisperKit transcriber

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Fallback `faster-whisper` y selección de motor

Implementa el motor de respaldo y la función `get_transcriber()` que elige el
motor según plataforma y configuración.

**Files:**
- Create: `backend/services/stt/faster_whisper.py`
- Modify: `backend/services/stt/__init__.py`
- Test: `backend/tests/test_stt_selection.py`

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/test_stt_selection.py`:

```python
import services.stt as stt
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
```

- [ ] **Step 2: Correr el test para verificar que falla**

```bash
pytest tests/test_stt_selection.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services.stt.faster_whisper'`.

- [ ] **Step 3: Implementar `backend/services/stt/faster_whisper.py`**

```python
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

    def _ensure_model(self):
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
```

- [ ] **Step 4: Reescribir `backend/services/stt/__init__.py`**

```python
"""Selección del motor de transcripción según plataforma y configuración."""
import functools
import os
import platform

from services.stt.base import Transcriber, TranscriptionResult  # noqa: F401
from services.stt.faster_whisper import FasterWhisperTranscriber
from services.stt.whisperkit import WhisperKitTranscriber


def _build_transcriber() -> Transcriber:
    engine = os.getenv("STT_ENGINE", "").strip().lower()
    if not engine:
        engine = "whisperkit" if platform.system() == "Darwin" else "faster_whisper"

    if engine == "whisperkit":
        return WhisperKitTranscriber(
            cli=os.getenv("WHISPERKIT_CLI", "whisperkit-cli"),
            model=os.getenv("WHISPERKIT_MODEL", "large-v3"),
            timeout=int(os.getenv("STT_TIMEOUT", "60")),
        )
    if engine == "faster_whisper":
        return FasterWhisperTranscriber(
            model_size=os.getenv("FASTER_WHISPER_MODEL", "small"),
        )
    raise ValueError(f"STT_ENGINE desconocido: {engine!r}")


@functools.lru_cache(maxsize=1)
def get_transcriber() -> Transcriber:
    """Devuelve el motor STT activo (singleton cacheado)."""
    return _build_transcriber()
```

- [ ] **Step 5: Correr los tests para verificar que pasan**

```bash
pytest tests/test_stt_selection.py tests/test_stt_base.py -v
```
Expected: PASS — 6 tests.

- [ ] **Step 6: Commit (milestone 5)**

```bash
but commit -m "feat(audio): add faster-whisper fallback

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Pipeline de orquestación y endpoint `/api/transcribe`

Une todo: `transcribe_audio()` orquesta el flujo y el endpoint expone el contrato
HTTP mapeando errores a códigos.

**Files:**
- Create: `backend/services/audio_pipeline.py`
- Replace: `backend/routes/audio.py`  (versión real, sustituye el stub de la Task 1)
- Test: `backend/tests/test_audio_pipeline.py`
- Test: `backend/tests/test_audio_route.py`

- [ ] **Step 1: Escribir los tests del pipeline que fallan**

`backend/tests/test_audio_pipeline.py`:

```python
import pytest

import services.audio_pipeline as pipeline
from services.audio_errors import AudioTooShortError, EmptyTranscriptionError
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


def test_empty_transcription_raises(monkeypatch, webm_2s):
    monkeypatch.setattr(
        pipeline, "get_transcriber", lambda: FakeTranscriber("   ")
    )
    with pytest.raises(EmptyTranscriptionError):
        pipeline.transcribe_audio(webm_2s)
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

```bash
pytest tests/test_audio_pipeline.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services.audio_pipeline'`.

- [ ] **Step 3: Implementar `backend/services/audio_pipeline.py`**

```python
"""Orquestación del audio pipeline: audio crudo -> texto transcrito."""
import os

from services.audio_convert import to_wav16k_mono
from services.audio_errors import (
    AudioTooLongError,
    AudioTooShortError,
    EmptyTranscriptionError,
)
from services.stt import get_transcriber

_MIN_DURATION = float(os.getenv("AUDIO_MIN_DURATION", "0.5"))
_MAX_DURATION = float(os.getenv("AUDIO_MAX_DURATION", "120"))


def transcribe_audio(audio_path: str) -> dict:
    """Convierte y transcribe un archivo de audio.

    Devuelve {"text": str, "duration": float}.
    Lanza subclases de AudioError ante audio inválido o fallo de transcripción.
    """
    wav_path, duration = to_wav16k_mono(audio_path)
    try:
        if duration < _MIN_DURATION:
            raise AudioTooShortError(
                f"El audio dura {duration:.2f}s (mínimo {_MIN_DURATION}s)."
            )
        if duration > _MAX_DURATION:
            raise AudioTooLongError(
                f"El audio dura {duration:.0f}s (máximo {_MAX_DURATION:.0f}s)."
            )
        result = get_transcriber().transcribe(wav_path)
        text = result.text.strip()
        if not text:
            raise EmptyTranscriptionError()
        return {"text": text, "duration": round(duration, 2)}
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)
```

- [ ] **Step 4: Correr los tests del pipeline para verificar que pasan**

```bash
pytest tests/test_audio_pipeline.py -v
```
Expected: PASS — 3 tests.

- [ ] **Step 5: Escribir los tests del endpoint que fallan**

`backend/tests/test_audio_route.py` — usa una app FastAPI mínima para aislar la
ruta de audio del resto del backend.

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.audio as audio_route
from services.audio_errors import AudioTooShortError


def _client():
    app = FastAPI()
    app.include_router(audio_route.router, prefix="/api")
    return TestClient(app)


def test_rejects_non_audio():
    r = _client().post(
        "/api/transcribe",
        files={"audio": ("x.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_rejects_empty_file():
    r = _client().post(
        "/api/transcribe",
        files={"audio": ("a.webm", b"", "audio/webm")},
    )
    assert r.status_code == 422


def test_rejects_too_large(monkeypatch):
    monkeypatch.setattr(audio_route, "_MAX_SIZE_BYTES", 50)
    r = _client().post(
        "/api/transcribe",
        files={"audio": ("a.webm", b"\x00" * 100, "audio/webm")},
    )
    assert r.status_code == 413


def test_happy_path(monkeypatch):
    monkeypatch.setattr(
        audio_route, "transcribe_audio",
        lambda path: {"text": "hola", "duration": 2.0},
    )
    r = _client().post(
        "/api/transcribe",
        files={"audio": ("a.webm", b"\x00" * 100, "audio/webm")},
    )
    assert r.status_code == 200
    assert r.json() == {"text": "hola", "duration": 2.0}


def test_maps_audio_error_to_http(monkeypatch):
    def boom(path):
        raise AudioTooShortError("muy corto")

    monkeypatch.setattr(audio_route, "transcribe_audio", boom)
    r = _client().post(
        "/api/transcribe",
        files={"audio": ("a.webm", b"\x00" * 100, "audio/webm")},
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "muy corto"
```

- [ ] **Step 6: Correr los tests del endpoint para verificar que fallan**

```bash
pytest tests/test_audio_route.py -v
```
Expected: FAIL — el stub actual devuelve 503; los tests esperan 400/422/413/200.

- [ ] **Step 7: Reemplazar `backend/routes/audio.py` con la versión real**

```python
"""Endpoint POST /api/transcribe — transcripción de voz a texto."""
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.audio_errors import AudioError
from services.audio_pipeline import transcribe_audio

router = APIRouter()

_MAX_SIZE_MB = int(os.getenv("AUDIO_MAX_SIZE_MB", "25"))
_MAX_SIZE_BYTES = _MAX_SIZE_MB * 1024 * 1024


class TranscribeResponse(BaseModel):
    text: str
    duration: float


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    content_type = audio.content_type or ""
    if not content_type.startswith("audio/"):
        raise HTTPException(400, "El archivo debe ser audio.")

    data = await audio.read()
    if not data:
        raise HTTPException(422, "El archivo de audio está vacío.")
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(
            413, f"El audio supera el límite de {_MAX_SIZE_MB} MB."
        )

    fd, tmp_path = tempfile.mkstemp(suffix=".audio")
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(data)
    try:
        return transcribe_audio(tmp_path)
    except AudioError as exc:
        raise HTTPException(exc.status_code, str(exc) or exc.detail)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
```

- [ ] **Step 8: Correr toda la suite rápida para verificar que pasa**

```bash
pytest -v
```
Expected: PASS — todos los tests; el de integración aparece `deselected`.

- [ ] **Step 9: Commit (milestone 6)**

```bash
but commit -m "feat(audio): wire pipeline and /api/transcribe endpoint

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Script de warmup

Pre-calienta el motor STT (descarga del modelo + compilación CoreML) para que el
primer request del demo no pague el arranque en frío.

**Files:**
- Create: `backend/scripts/warmup_audio.py`

- [ ] **Step 1: Implementar `backend/scripts/warmup_audio.py`**

```python
"""Pre-calienta el motor STT antes del demo.

Genera voz real con el TTS de macOS (`say`) y la pasa por el pipeline completo.
Esto fuerza la descarga del modelo y la compilación CoreML (lentas la primera
vez). Correr ANTES del demo, desde backend/:

    python scripts/warmup_audio.py
"""
import os
import subprocess
import sys
import tempfile

# Permite importar el paquete `services` al correr el script directamente.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.audio_pipeline import transcribe_audio  # noqa: E402


def main() -> int:
    fd, aiff = tempfile.mkstemp(suffix=".aiff")
    os.close(fd)
    subprocess.run(
        ["say", "-o", aiff, "hola, esto es una prueba de calentamiento"],
        check=True,
    )
    try:
        print("Calentando motor STT (descarga + compilación CoreML)...")
        result = transcribe_audio(aiff)
        print(f"Motor STT listo. Transcripción de prueba: {result['text']!r}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Warmup falló: {exc}", file=sys.stderr)
        return 1
    finally:
        if os.path.exists(aiff):
            os.unlink(aiff)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verificar que el script corre**

```bash
python scripts/warmup_audio.py
```
Expected: imprime "Motor STT listo. Transcripción de prueba: '...'" y sale con
código 0. (Si el modelo ya se descargó en la Task 4, es rápido.)

- [ ] **Step 3: Commit (milestone 7)**

```bash
but commit -m "feat(audio): add startup warmup script

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Contrato de audio para el frontend

Documento cross-team para quien construya la UI de grabación.

**Files:**
- Create: `docs/AUDIO_CONTRACT.md`  (raíz del repo)

- [ ] **Step 1: Crear `docs/AUDIO_CONTRACT.md`**

```markdown
# Contrato de audio — `POST /api/transcribe`

Para quien construya la UI de grabación. El backend de audio garantiza este
contrato; la UI solo debe cumplir con el formato de envío.

## Request

- **Método/ruta:** `POST /api/transcribe`
- **Content-Type:** `multipart/form-data`
- **Campo:** `audio` — el archivo de audio grabado.

## Response

`200 OK` — JSON:

```json
{ "text": "la transcripción en español", "duration": 12.4 }
```

## Formatos aceptados

El backend reconvierte con `ffmpeg`, así que acepta cualquier formato que
`ffmpeg` decodifique:

- **Chrome / Android:** `audio/webm` (códec Opus) — default de `MediaRecorder`.
- **Safari / iOS:** `audio/mp4` (códec AAC).

La UI **no** necesita forzar sample rate ni canales; el backend normaliza a
WAV 16 kHz mono.

## Límites

- Duración: **0.5 s – 120 s**.
- Tamaño: **≤ 25 MB**.

## Errores

Todos devuelven JSON `{ "detail": "mensaje en español" }`:

| Código | Causa |
|--------|-------|
| `400` | El archivo no es audio (`Content-Type` no empieza con `audio/`). |
| `413` | El archivo supera 25 MB. |
| `422` | Audio vacío, corrupto, muy corto, muy largo, o sin voz detectable. |
| `504` | La transcripción tardó demasiado. |
| `500` / `503` | Fallo o indisponibilidad del motor de transcripción. |

## Aviso importante para iOS

Safari en iOS produce `audio/mp4`, no `audio/webm`. La UI **no debe hardcodear**
el MIME type del `Blob`. Debe usar el MIME real del `MediaRecorder`:

```js
const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
```

> Nota: el `app.js` actual hardcodea `audio/webm` en la línea ~110. Eso rompe la
> grabación en iPhone y debe corregirse al implementar la UI (fuera del alcance
> del audio pipeline).
```

- [ ] **Step 2: Commit (milestone 8)**

```bash
but commit -m "docs(audio): add audio contract for frontend

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Verificación final

Con las 8 tasks completas, desde `backend/` con el venv activado:

- [ ] `pytest -v` — toda la suite rápida en verde.
- [ ] `pytest -m integration -v -s` — el test real de WhisperKit en verde.
- [ ] `python scripts/warmup_audio.py` — sale con código 0.
- [ ] `but status` — 8 commits en `feat/audio-pipeline`, sin cambios sin asignar.

## Notas de divergencia respecto al spec

- `get_transcriber()` se implementa en la Task 5 (no en la 3), para que cada
  commit deje el árbol verde — `stt/__init__.py` no puede importar motores que
  aún no existen.
- Se añadió `EngineUnavailableError` (HTTP 503) y `AudioTooLongError` (HTTP 422),
  no nombrados explícitamente en la tabla de errores del spec pero implícitos en
  sus límites (0.5–120 s) y casos de motor no disponible.
- `WHISPERKIT_MODEL` arranca en `large-v3` (identificador garantizado). El spec
  menciona `large-v3-turbo` como objetivo; basta cambiar la variable de entorno
  si esa variante está disponible.
- Se descartó el método `warmup()` en el `Protocol` (YAGNI): el calentamiento es
  responsabilidad del script `scripts/warmup_audio.py`, que llama al pipeline
  normal.
- El spec §11 menciona `pytest-asyncio`; el plan solo agrega `pytest` porque
  ningún test es `async def` (los tests del endpoint usan `TestClient`, que es
  síncrono). Se puede agregar después si hace falta.
