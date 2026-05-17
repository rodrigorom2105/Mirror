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
