from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.emotion as emotion_route


def _client():
    app = FastAPI()
    app.include_router(emotion_route.router, prefix="/api")
    return TestClient(app)


def test_entry_analyzes_without_saving(monkeypatch):
    calls = {"save": 0}
    monkeypatch.setattr(emotion_route, "extract_ruler",
                        lambda text: {"emocion_primaria": "tenso", "cuadrante": "rojo"})

    def fake_save(ruler):
        calls["save"] += 1
        return (1, "2026-05-17T00:00:00")
    monkeypatch.setattr(emotion_route, "save_entry", fake_save)

    import services.audio_pipeline as ap
    monkeypatch.setattr(ap, "transcribe_audio",
                        lambda path: {"text": "hola", "duration": 2.0})

    r = _client().post(
        "/api/entry",
        files={"audio": ("a.webm", b"\x00" * 100, "audio/webm")},
        data={"emocion_seleccionada": "tenso"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["emocion_seleccionada"] == "tenso"
    assert body["transcripcion"] == "hola"
    assert "id" not in body
    assert calls["save"] == 0


def test_save_persists_and_returns_id(monkeypatch):
    saved = {}
    calls = {"update_profile": 0, "acompanamiento": 0}

    def fake_save(ruler):
        saved["ruler"] = ruler
        return (7, "2026-05-17T01:00:00")
    monkeypatch.setattr(emotion_route, "save_entry", fake_save)

    def fake_update_profile(ruler, bg):
        calls["update_profile"] += 1
    monkeypatch.setattr(emotion_route, "_update_profile", fake_update_profile)

    def fake_acompanamiento():
        calls["acompanamiento"] += 1
        return None
    monkeypatch.setattr(emotion_route, "_acompanamiento_post_entry", fake_acompanamiento)

    r = _client().post("/api/save",
                        json={"emocion_primaria": "tenso", "cuadrante": "rojo"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 7
    assert saved["ruler"]["emocion_primaria"] == "tenso"
    assert calls["update_profile"] == 1, "_update_profile debe llamarse exactamente una vez"
    assert calls["acompanamiento"] == 1, "_acompanamiento_post_entry debe llamarse exactamente una vez"
    assert "acompanamiento" in body, "la respuesta debe incluir la clave 'acompanamiento'"
    assert body["acompanamiento"] is None
