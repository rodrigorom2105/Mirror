from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.emotion as emotion_route


def _client():
    app = FastAPI()
    app.include_router(emotion_route.router, prefix="/api")
    return TestClient(app)


def _patch_analysis(monkeypatch, ruler):
    """Mockea extract_ruler + feedback para no tocar el LLM en las pruebas."""
    monkeypatch.setattr(emotion_route, "extract_ruler", lambda text: dict(ruler))
    monkeypatch.setattr(emotion_route, "generate_entry_feedback",
                        lambda *a, **k: {"mensaje": "Aquí estoy.", "modo": "apoyo"})


def test_entry_analyzes_without_saving(monkeypatch):
    calls = {"save": 0}
    _patch_analysis(monkeypatch, {"emocion_primaria": "tenso", "cuadrante": "rojo",
                                  "intensidad": 6})

    def fake_save(ruler):
        calls["save"] += 1
        return ("id-1", "2026-05-17T00:00:00")
    monkeypatch.setattr(emotion_route, "save_entry", fake_save)

    import services.audio_pipeline as ap
    monkeypatch.setattr(ap, "transcribe_audio",
                        lambda path: {"text": "hola", "duration": 2.0})

    r = _client().post(
        "/api/entry",
        files={"audio": ("a.webm", b"\x00" * 100, "audio/webm")},
        data={"emocion_seleccionada": "tenso", "client_time": "2026-05-17T21:00:00-06:00"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["transcripcion"] == "hola"
    assert body["feedback"]["mensaje"] == "Aquí estoy."
    assert "id" not in body
    assert calls["save"] == 0


def test_analyze_returns_feedback_and_intensity(monkeypatch):
    _patch_analysis(monkeypatch, {"emocion_primaria": "ansioso", "cuadrante": "rojo",
                                  "intensidad": 5, "emociones_secundarias": []})
    r = _client().post("/api/analyze", json={
        "text": "tuve un día pesado", "emocion_seleccionada": "ansioso",
        "client_time": "2026-05-17T21:00:00-06:00"})
    assert r.status_code == 200
    body = r.json()
    assert body["feedback"]["modo"] == "apoyo"
    assert 1 <= body["intensidad"] <= 10
    assert body["transcripcion"] == "tuve un día pesado"


def test_save_persists_and_flattens_feedback(monkeypatch):
    saved = {}
    calls = {"update_profile": 0}

    def fake_save(ruler):
        saved["ruler"] = ruler
        return ("id-7", "2026-05-17T01:00:00")
    monkeypatch.setattr(emotion_route, "save_entry", fake_save)

    def fake_update_profile(ruler, bg):
        calls["update_profile"] += 1
    monkeypatch.setattr(emotion_route, "_update_profile", fake_update_profile)

    r = _client().post("/api/save", json={
        "emocion_primaria": "tenso", "cuadrante": "rojo",
        "feedback": {"mensaje": "Te acompaño.", "modo": "apoyo"},
        "reaccion_feedback": "me_ayudo"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "id-7"
    assert "acompanamiento" not in body
    assert saved["ruler"]["feedback_mensaje"] == "Te acompaño."
    assert saved["ruler"]["feedback_modo"] == "apoyo"
    assert saved["ruler"]["feedback_reaccion"] == "me_ayudo"
    assert "feedback" not in saved["ruler"]
    assert calls["update_profile"] == 1


def test_save_tolerates_non_dict_feedback(monkeypatch):
    monkeypatch.setattr(emotion_route, "save_entry",
                        lambda ruler: ("id-9", "2026-05-17T02:00:00"))
    monkeypatch.setattr(emotion_route, "_update_profile", lambda ruler, bg: None)
    # Un payload malformado (feedback no-dict) no debe causar un 500.
    r = _client().post("/api/save", json={
        "emocion_primaria": "tenso", "cuadrante": "rojo", "feedback": "basura"})
    assert r.status_code == 200


def test_feedback_reaction_endpoint(monkeypatch):
    seen = {}

    def fake_set(entry_id, reaccion):
        seen["entry_id"] = entry_id
        seen["reaccion"] = reaccion
        return True
    monkeypatch.setattr(emotion_route, "set_feedback_reaction", fake_set)

    r = _client().post("/api/feedback/reaction",
                        json={"entry_id": "id-7", "reaccion": "me_ayudo"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert seen == {"entry_id": "id-7", "reaccion": "me_ayudo"}


def test_emotions_endpoint_returns_catalog():
    r = _client().get("/api/emotions")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"rojo", "amarillo", "azul", "verde"}
    assert len(body["rojo"]["emotions"]) == 12
