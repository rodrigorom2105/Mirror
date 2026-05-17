from services.entry_feedback import (
    compute_intensity,
    franja_horaria,
    select_mode,
)


def test_intensity_varies_with_selected_emotion():
    # "nervioso" (pos 0, leve) vs "furioso" (pos 11, intensa); mismo contenido.
    ruler = {"intensidad": 5, "emociones_secundarias": []}
    leve = compute_intensity(ruler, "nervioso")
    intensa = compute_intensity(ruler, "furioso")
    assert intensa > leve


def test_intensity_clamped_1_10():
    ruler = {"intensidad": 99, "emociones_secundarias": []}
    assert 1 <= compute_intensity(ruler, "furioso") <= 10


def test_intensity_falls_back_to_content_when_emotion_unknown():
    ruler = {"intensidad": 7, "emociones_secundarias": []}
    assert compute_intensity(ruler, "inexistente") == 7


def test_intensity_clamped_lower_bound():
    # Emoción desconocida → solo contenido; intensidad 0 sube al piso de 1.
    ruler = {"intensidad": 0, "emociones_secundarias": []}
    assert compute_intensity(ruler, "inexistente") == 1


def test_intensity_blends_secondary_emotions():
    # Las secundarias leves bajan la intensidad respecto a solo la primaria.
    base = compute_intensity({"intensidad": 8, "emociones_secundarias": []}, "furioso")
    con_sec = compute_intensity(
        {"intensidad": 8, "emociones_secundarias": ["nervioso", "inquieto"]}, "furioso")
    assert con_sec < base


def test_franja_horaria_buckets():
    assert franja_horaria("2026-05-17T03:00:00-06:00")[0] == "madrugada"
    assert franja_horaria("2026-05-17T09:00:00-06:00")[0] == "mañana"
    assert franja_horaria("2026-05-17T15:00:00-06:00")[0] == "tarde"
    assert franja_horaria("2026-05-17T21:00:00-06:00")[0] == "noche"


def test_franja_horaria_invalid_falls_back():
    franja, dia = franja_horaria(None)
    assert franja in {"madrugada", "mañana", "tarde", "noche"}
    assert dia


def test_select_mode_apoyo_for_negative_intense():
    assert select_mode({"cuadrante": "rojo", "intensidad": 8}) == "apoyo"
    assert select_mode({"cuadrante": "azul", "intensidad": 9}) == "apoyo"


def test_select_mode_ligero_otherwise():
    assert select_mode({"cuadrante": "verde", "intensidad": 9}) == "ligero"
    assert select_mode({"cuadrante": "amarillo", "intensidad": 8}) == "ligero"
    assert select_mode({"cuadrante": "rojo", "intensidad": 4}) == "ligero"


def test_select_mode_boundary_at_5():
    # El umbral es estricto (> 5): 5 es ligero, 5.1 es apoyo.
    assert select_mode({"cuadrante": "rojo", "intensidad": 5}) == "ligero"
    assert select_mode({"cuadrante": "rojo", "intensidad": 5.1}) == "apoyo"


def test_generate_entry_feedback_returns_message_and_mode(monkeypatch):
    import services.entry_feedback as ef

    monkeypatch.setattr(ef, "_build_evidence", lambda *a, **k: "EVIDENCIA")

    import services.llm_service as llm
    monkeypatch.setattr(llm, "_ollama_generate",
                        lambda system, user, **k: "Te acompaño en esto.")

    out = ef.generate_entry_feedback(
        {"cuadrante": "rojo", "intensidad": 8, "emocion_primaria": "ansioso"},
        "ansioso", "2026-05-17T21:00:00-06:00")
    assert out["modo"] == "apoyo"
    assert out["mensaje"] == "Te acompaño en esto."


def test_generate_entry_feedback_never_raises(monkeypatch):
    import services.entry_feedback as ef
    import services.llm_service as llm

    def boom(*a, **k):
        raise RuntimeError("LLM caído")
    monkeypatch.setattr(llm, "_ollama_generate", boom)
    monkeypatch.setattr(ef, "_build_evidence", lambda *a, **k: "EVIDENCIA")

    out = ef.generate_entry_feedback(
        {"cuadrante": "verde", "intensidad": 3}, "tranquilo", None)
    assert out["modo"] == "ligero"
    assert out["mensaje"] == ef._FALLBACK  # mensaje de respaldo cálido
