from services.emotion_catalog import (
    emotion_position,
    get_catalog,
    position_intensity,
)


def test_catalog_has_four_quadrants_of_twelve():
    cat = get_catalog()
    assert set(cat.keys()) == {"rojo", "amarillo", "azul", "verde"}
    for q in cat.values():
        assert len(q["emotions"]) == 12
        assert q["name"] and q["icon"]


def test_emotion_position_orders_low_to_high():
    # "nervioso" es la primera de rojo, "furioso" la última.
    assert emotion_position("nervioso") == 0
    assert emotion_position("furioso") == 11


def test_emotion_position_ignores_accents_and_case():
    assert emotion_position("EUFÓRICO") == emotion_position("euforico")
    assert emotion_position("euforico") is not None


def test_emotion_position_unknown_returns_none():
    assert emotion_position("inexistente") is None


def test_emotion_position_none_returns_none():
    assert emotion_position(None) is None


def test_position_intensity_maps_to_1_10():
    assert position_intensity(0) == 1.0
    assert position_intensity(11) == 10.0
    assert 1.0 < position_intensity(5) < 10.0
