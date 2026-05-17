from dotenv import load_dotenv
load_dotenv()

import time
from contextlib import asynccontextmanager

from logging_config import DEV_MODE, get_logger, setup_logging

setup_logging()
_log = get_logger("api")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from routes import audio, emotion, history, chat

class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa la base SQLite (perfil consolidado + sesiones de chat).
    try:
        from services.db import init_db
        init_db()
        print("[startup] Base SQLite lista.", flush=True)
    except Exception as exc:  # noqa: BLE001 - no debe tumbar el arranque
        print(f"[startup] init_db omitido: {exc}", flush=True)

    # Calienta el motor STT al arrancar: la primera carga del modelo en CoreML
    # es lenta. Pagar ese costo aquí evita que la primera grabación real del
    # usuario se pase del STT_TIMEOUT.
    try:
        from services.audio_pipeline import warmup
        warmup()
        print("[startup] STT warm-up completado.", flush=True)
    except Exception as exc:  # noqa: BLE001 - el warm-up nunca debe tumbar el arranque
        print(f"[startup] STT warm-up omitido: {exc}", flush=True)
    yield


app = FastAPI(
    title="Mirror API",
    default_response_class=UTF8JSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if DEV_MODE:
    @app.middleware("http")
    async def _log_requests(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        _log.info(
            "%s %s → %s (%.0f ms)",
            request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response

app.include_router(audio.router, prefix="/api")
app.include_router(emotion.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

if __name__ == "__main__":
    import argparse
    import os
    import uvicorn

    # Modelos de transcripción de voz disponibles (WhisperKit, el motor por
    # defecto en macOS), ordenados de más rápido/ligero a más preciso/pesado.
    _STT_MODELS = ["tiny", "base", "small", "large-v2", "large-v3",
                   "large-v3-turbo", "distil-large-v3"]
    parser = argparse.ArgumentParser(description="Servidor de Mirror.")
    parser.add_argument(
        "--stt-model", choices=_STT_MODELS, metavar="MODELO",
        help="Modelo de transcripción de voz. Opciones: "
             + ", ".join(_STT_MODELS) + ". Por defecto: el de .env.",
    )
    args = parser.parse_args()
    if args.stt_model:
        # Se exporta al entorno antes de arrancar; services/stt lo lee al
        # construir el transcriptor. load_dotenv() no lo sobreescribe.
        os.environ["WHISPERKIT_MODEL"] = args.stt_model
        os.environ["FASTER_WHISPER_MODEL"] = args.stt_model
        print(f"[startup] Modelo STT por flag: {args.stt_model}", flush=True)

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
