from services.signals_engine import Signal, classify_state


def test_classify_state_estable_sin_senales():
    assert classify_state([]) == "estable"


def test_classify_state_en_dificultad():
    s = Signal(tipo="emocion_negativa_intensa", titulo="x")
    assert classify_state([s]) == "en_dificultad"


def test_classify_state_volatil():
    s = Signal(tipo="intensidad_anomala", titulo="x")
    assert classify_state([s]) == "volatil"


def test_classify_state_en_mejora():
    s = Signal(tipo="tendencia_valencia", titulo="x", evidencia={"delta": 0.4})
    assert classify_state([s]) == "en_mejora"


def test_classify_state_tendencia_negativa_es_dificultad():
    s = Signal(tipo="tendencia_valencia", titulo="x", evidencia={"delta": -0.4})
    assert classify_state([s]) == "en_dificultad"


def test_classify_state_desconectado():
    s = Signal(tipo="ausencia_registro", titulo="x")
    assert classify_state([s]) == "desconectado"
