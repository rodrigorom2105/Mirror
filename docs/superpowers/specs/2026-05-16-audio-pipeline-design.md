# Audio Pipeline — Design Spec

- **Proyecto:** Mirror (Guadalahacks 2026 — Edge AI)
- **Fecha:** 2026-05-16
- **Responsable:** Max Rojas — Persona 1 / Audio Engineer
- **Branch:** `feat/audio-pipeline` (GitButler, target `origin/dev`)

---

## 1. Contexto y objetivo

Mirror es una PWA de autoconocimiento emocional 100% local. El usuario graba voz
explicando cómo se siente; el backend la transcribe a texto en español y el resto
del sistema (LLM, memoria vectorial) extrae estructura emocional.

El **audio pipeline** es la entrada de ese flujo: convierte audio del navegador en
texto transcrito confiable en español, rápido, sin servicios en la nube.

**Criterio de éxito:** dado un audio grabado en el celular, `POST /api/transcribe`
devuelve la transcripción en español en un tiempo aceptable para un demo en vivo
(presupuesto ~3–5 s; el riesgo documentado del proyecto es "audio→respuesta >8 s").

## 2. Alcance

### Dentro de alcance

- Motor STT multi-backend con abstracción `Transcriber`.
- `WhisperKitTranscriber` (primario, macOS / Apple Silicon).
- `FasterWhisperTranscriber` (fallback ligero, opcional).
- Conversión de formato (audio del navegador → WAV 16 kHz mono) vía `ffmpeg`.
- Endpoint `POST /api/transcribe`.
- Manejo de errores explícito con códigos HTTP.
- Entorno virtual (`venv`) aislado y tests con `pytest`.
- `docs/AUDIO_CONTRACT.md` — contrato documentado para quien construya la UI.

### Fuera de alcance (otra persona)

- UI de grabación / cualquier cambio a `frontend/app.js`.
- Modo de entrada por texto (parte de la idea "multimodal", pero es trabajo de UI).
- Endpoint orquestado `/api/entry` (Persona 4 — Integration Lead).
- `crisis_keywords.py` ya existe y funciona; no se modifica aquí.

## 3. Decisiones tomadas (con rationale)

| Decisión | Elección | Por qué |
|---|---|---|
| Motor primario | WhisperKit vía `whisperkit-cli` | Optimizado para Apple Silicon (CoreML / Neural Engine); el backend del demo corre en la Mac de Max. |
| Patrón de integración | Enfoque A: `whisperkit-cli` como subproceso por request, con warmup | Simple y robusto para un hackathon; sin gestión de procesos hijo. La capa `Transcriber` deja listo el Enfoque B (server caliente) sin reescribir nada. |
| Conversión de audio | `ffmpeg` directo por subproceso (no `pydub`) | Evita la dependencia `audioop`, removida en Python 3.13+. Version-agnóstico. |
| Modelo | `large-v3-turbo` | Rápido en ANE y fuerte en español. Bajable a `base`/`small` si la descarga o velocidad estorban. |
| Fallback | `faster-whisper`, opcional / comentado en requirements | Solo es seguro de portabilidad; el demo corre en Mac. Mantenerlo opcional esquiva el riesgo de wheels en Python 3.14. |
| Entorno Python | `venv` con **Python 3.13** en `backend/.venv` | 3.13 (ya instalado vía `python@3.13`) es más maduro que el 3.14.5 del sistema: más wheels para deps nativas (`ctranslate2`, `chromadb`). Instalar global es sucio y arriesgado. |

## 4. Setup del entorno

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install whisperkit-cli
```

- Se usa **Python 3.13** (ya instalado vía Homebrew, `python@3.13`), no el
  3.14.5 del sistema: 3.13 es más maduro y tiene más wheels para dependencias
  con código nativo (`ctranslate2` de `faster-whisper`, `chromadb`). El audio
  pipeline en sí es agnóstico a la versión — todo lo pesado es subproceso
  (`ffmpeg`, `whisperkit-cli`).
- `backend/.venv/` ya está cubierto por `.gitignore` (`venv/`, `.venv/`).
- Todas las dependencias y `pytest` se instalan en el venv, nunca global.
- Los tests se corren siempre con el venv activo.

## 5. Arquitectura y componentes

```
backend/
├── routes/
│   └── audio.py            # POST /api/transcribe — valida, delega, mapea errores→HTTP
├── services/
│   ├── audio_pipeline.py   # transcribe_audio() — orquesta el flujo completo
│   ├── audio_convert.py    # ffmpeg: cualquier formato → wav 16kHz mono + duración
│   ├── audio_errors.py     # jerarquía de excepciones del pipeline
│   └── stt/
│       ├── __init__.py     # get_transcriber() — elige motor por plataforma/config
│       ├── base.py         # Transcriber (Protocol) + TranscriptionResult
│       ├── whisperkit.py   # motor primario — whisperkit-cli como subproceso
│       └── faster_whisper.py  # motor fallback (carga perezosa, opcional)
├── scripts/
│   └── warmup_audio.py     # fuerza la compilación CoreML antes del demo
└── tests/                  # suite de pytest

docs/
└── AUDIO_CONTRACT.md       # contrato cross-team para quien haga la UI (raíz del repo)
```

El `backend/services/whisper_service.py` actual (stub con whisper.cpp) se elimina;
lo reemplaza `audio_pipeline.py`.

### Responsabilidad de cada unidad

| Archivo | Qué hace | Depende de |
|---|---|---|
| `audio_pipeline.py` | `transcribe_audio(path) -> dict`. Orquesta: convertir → validar → transcribir → validar resultado. **Función pública** que importan el endpoint y `/api/entry` de P4. | `audio_convert`, `stt`, `audio_errors` |
| `audio_convert.py` | `to_wav16k_mono(path) -> (wav_path, duration)`. Subproceso `ffmpeg`. | `ffmpeg` |
| `audio_errors.py` | `AudioError` y subclases: `AudioCorruptError`, `AudioTooShortError`, `EmptyTranscriptionError`, `TranscriptionFailedError`, `TranscriptionTimeout`. | — |
| `stt/base.py` | `Transcriber` (Protocol con `transcribe(wav_path) -> TranscriptionResult`). Aísla el motor. | — |
| `stt/whisperkit.py` | Implementa `Transcriber` ejecutando `whisperkit-cli transcribe --language es`. Parsea salida, maneja exit code y timeout. | `whisperkit-cli` |
| `stt/faster_whisper.py` | Implementa `Transcriber` con `faster-whisper` en proceso. Import perezoso: si no está instalado, no rompe nada. | `faster-whisper` (opcional) |
| `stt/__init__.py` | `get_transcriber()` — singleton cacheado; elige WhisperKit en macOS, fallback en otros. Punto de enchufe del Enfoque B. | todo `stt/` |
| `scripts/warmup_audio.py` | Corre una transcripción de un wav corto para forzar la compilación CoreML del modelo. Se ejecuta antes del demo. | `stt` |

**Requisito "dejar B listo":** el endpoint y `audio_pipeline.py` solo conocen el
`Protocol` `Transcriber`. Migrar al server caliente (Enfoque B) es agregar
`stt/whisperkit_server.py` y cambiar `get_transcriber()`. Cero cambios fuera de `stt/`.

## 6. Flujo de datos

```
Frontend ──POST multipart/form-data {audio}──> /api/transcribe
                                                    │
  routes/audio.py:  valida content-type + tamaño ───┤
                    guarda a archivo temporal       │
                                                    ▼
  audio_pipeline.transcribe_audio(tmp):
     1. audio_convert.to_wav16k_mono()  ── ffmpeg ──> wav 16k mono + duración
     2. valida duración (mín 0.5 s / máx 120 s)
     3. get_transcriber()  ── singleton ──> WhisperKitTranscriber
     4. transcriber.transcribe(wav)  ── whisperkit-cli, con timeout ──> texto
     5. valida texto no vacío
     6. limpia archivos temporales
                                                    │
                          {text, duration}  <───────┘
  routes/audio.py:  excepción → código HTTP, o 200 con JSON
```

**Warmup:** la primera invocación de WhisperKit compila el modelo CoreML (lento,
una sola vez). Se mitiga con `scripts/warmup_audio.py` corrido antes del demo, más
un warmup perezoso en `get_transcriber()` como red de seguridad. No se toca
`main.py` (es de P4); opcionalmente se le sugiere a P4 una línea en su `startup`.

## 7. Manejo de errores

Cada error se detecta en su capa y se mapea a un código HTTP con mensaje en español:

| Caso | Capa que detecta | Excepción | HTTP |
|---|---|---|---|
| Content-type no es audio | `routes/audio.py` | — | `400` |
| Archivo > 25 MB | `routes/audio.py` | — | `413` |
| Audio corrupto / `ffmpeg` falla | `audio_convert` | `AudioCorruptError` | `422` |
| Audio < 0.5 s | `audio_pipeline` | `AudioTooShortError` | `422` |
| `whisperkit-cli` excede timeout | `stt/whisperkit` | `TranscriptionTimeout` | `504` |
| `whisperkit-cli` sale con error | `stt/whisperkit` | `TranscriptionFailedError` | `500` |
| Transcripción vacía (silencio) | `audio_pipeline` | `EmptyTranscriptionError` | `422` |
| Binario STT no disponible | `stt/__init__` | `TranscriptionFailedError` | `503` |

Respuesta de error: `{"detail": "mensaje claro"}`. El route tiene un único bloque
que traduce `AudioError → HTTPException`.

## 8. Testing

Implementación con TDD: test que falla → implementación → verde. Tests en
`backend/tests/`, corridos dentro del venv.

| Archivo | Cubre | Estrategia |
|---|---|---|
| `test_audio_convert.py` | webm→wav, mp4→wav, 16k mono correcto, archivo corrupto lanza error | Fixtures de audio reales pequeños |
| `test_stt_whisperkit.py` | Parseo de salida del CLI, exit code, timeout | Subproceso mockeado (rápido, sin modelo) |
| `test_audio_pipeline.py` | Audio corto→error, vacío→error, happy path→`{text,duration}` | `Transcriber` fake inyectado |
| `test_audio_route.py` | Endpoint: 200 happy + 400/413/422/504 | `TestClient` + transcriber fake |
| `test_integration_whisperkit.py` | Transcripción real end-to-end | `@pytest.mark.integration`; corre WhisperKit con un wav fixture con una frase conocida en español; se salta por defecto |

**Fixtures:** silencio y tono generados con `ffmpeg` para tests de conversión y
errores; para el test de integración, un clip corto real grabado
("hola, me siento un poco abrumado por el trabajo") commiteado (~50–100 KB).

## 9. Contrato de audio (`docs/AUDIO_CONTRACT.md`)

Para quien construya la UI de grabación:

- `POST /api/transcribe`, `multipart/form-data`, campo `audio`. Respuesta `{text, duration}`.
- Acepta cualquier formato que decodifique `ffmpeg` (webm/opus de Chrome,
  mp4/aac de Safari iOS). El backend reconvierte — el frontend no fuerza sample rate.
- Límites: duración 0.5–120 s, tamaño ≤ 25 MB.
- Errores: códigos HTTP + `{"detail": "..."}`.
- **Aviso iOS:** Safari produce `audio/mp4`. El frontend NO debe hardcodear
  `audio/webm` en el `Blob` (bug actual en `app.js:110`) — debe usar
  `mediaRecorder.mimeType`. Se documenta aquí; no se corrige en este alcance.

## 10. Configuración (`.env.example`)

Nuevas llaves; se quitan las de whisper.cpp (`WHISPER_CPP_PATH`, `WHISPER_MODEL`):

```
STT_ENGINE=whisperkit
WHISPERKIT_MODEL=large-v3-turbo
WHISPERKIT_CLI=whisperkit-cli
FASTER_WHISPER_MODEL=small
STT_TIMEOUT=60
AUDIO_MIN_DURATION=0.5
AUDIO_MAX_DURATION=120
AUDIO_MAX_SIZE_MB=25
```

## 11. Dependencias (`requirements.txt`)

- Se quita `pydub` (reemplazado por `ffmpeg` directo).
- `faster-whisper` queda comentado / opcional: solo se instala si se necesita el
  fallback. Con Python 3.13 sus wheels nativas (`ctranslate2`) son más probables,
  pero al ser solo seguro de portabilidad se mantiene fuera del set por defecto.
- Se agregan `pytest` y `pytest-asyncio` como dependencias de desarrollo.

## 12. Milestones de commits (GitButler `but`)

Cada milestone queda funcional y testeado antes de su commit:

| # | Commit | Contenido |
|---|---|---|
| 1 | `chore(audio): scaffold STT structure, venv and config` | estructura de carpetas, `audio_errors.py`, `.env.example`, `requirements.txt`, venv creado |
| 2 | `feat(audio): add ffmpeg conversion service` | `audio_convert.py` + tests |
| 3 | `feat(audio): add Transcriber abstraction` | `stt/base.py`, `stt/__init__.py` |
| 4 | `feat(audio): add WhisperKit transcriber` | `stt/whisperkit.py` + tests + instalación de `whisperkit-cli` |
| 5 | `feat(audio): add faster-whisper fallback` | `stt/faster_whisper.py` |
| 6 | `feat(audio): wire pipeline and /api/transcribe endpoint` | `audio_pipeline.py`, `routes/audio.py` + tests |
| 7 | `feat(audio): add startup warmup script` | `scripts/warmup_audio.py` |
| 8 | `docs(audio): add audio contract for frontend` | `docs/AUDIO_CONTRACT.md` |

## 13. Futuro / fuera de alcance

- **Enfoque B (WhisperKit Local Server):** modelo caliente para latencia menor.
  La abstracción `Transcriber` lo deja listo; se implementa solo si la latencia
  del Enfoque A estorba en pruebas.
- Streaming de transcripción en tiempo real (no requerido por el MVP).
- Soporte multi-idioma (el MVP es solo español).
