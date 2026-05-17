# Feedback Emocional Contextual + Pulido de UX — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar feedback emocional contextual de la IA al registrar emociones, con intensidad dinámica 60/40 y hora local, y pulir el frontend (grabación tap/hold, transiciones, loading, pantalla de resultados, drawer, modo noche).

**Architecture:** El feedback se genera en un módulo backend nuevo (`entry_feedback.py`) llamado desde los endpoints de análisis, no después de guardar. La intensidad se calcula en código combinando la posición de la emoción en un catálogo unificado (60%) con la señal del LLM (40%). El frontend consume el catálogo vía `GET /api/emotions`, rehace la máquina de estados de grabación, y añade un bottom drawer reutilizable.

**Tech Stack:** FastAPI + Ollama (`qwen3:4b-instruct`) + ChromaDB en el backend; PWA vanilla HTML/CSS/JS en el frontend; pytest para el backend.

**Spec:** `docs/superpowers/specs/2026-05-17-feedback-emocional-design.md`

**Convenciones de prueba:**
- Backend: `cd backend && .venv/bin/python -m pytest -q` (config en `backend/pytest.ini`, `pythonpath=.`, `testpaths=tests`).
- Frontend: no hay framework de pruebas JS. Verificación = `node --check frontend/app.js` (sintaxis) + verificación en navegador con Chrome DevTools MCP.

---

## Task 1: Catálogo de emociones unificado

Fuente única de las 4 listas ordenadas de emociones. La base del cálculo de intensidad (Task 2) y del catálogo que consume el frontend (Task 6).

**Files:**
- Create: `backend/data/emotion_catalog.json`
- Create: `backend/services/emotion_catalog.py`
- Test: `backend/tests/test_emotion_catalog.py`

- [ ] **Step 1: Crear el JSON del catálogo**

Crear `backend/data/emotion_catalog.json` con las 4 listas (orden idéntico al `QUADRANTS` actual de `frontend/app.js`, de leve a intensa):

```json
{
  "rojo": {
    "name": "Alta tensión",
    "icon": "flame",
    "axisTop": "Más alterado",
    "axisBottom": "Más calmado",
    "axisSide": "Más desagradable",
    "emotions": ["nervioso", "inquieto", "preocupado", "tenso", "ansioso", "irritado", "molesto", "frustrado", "estresado", "abrumado", "enojado", "furioso"]
  },
  "amarillo": {
    "name": "Energía positiva",
    "icon": "sun",
    "axisTop": "Más intenso",
    "axisBottom": "Más sereno",
    "axisSide": "Más agradable",
    "emotions": ["optimista", "motivado", "animado", "alegre", "feliz", "entusiasmado", "inspirado", "orgulloso", "emocionado", "sorprendido", "eufórico", "radiante"]
  },
  "azul": {
    "name": "Baja energía",
    "icon": "cloud-rain",
    "axisTop": "Más leve",
    "axisBottom": "Más hundido",
    "axisSide": "Más desagradable",
    "emotions": ["desganado", "aburrido", "nostálgico", "melancólico", "desanimado", "decepcionado", "triste", "solo", "agotado", "vacío", "derrotado", "abatido"]
  },
  "verde": {
    "name": "Paz interior",
    "icon": "leaf",
    "axisTop": "Más activo",
    "axisBottom": "Más profundo",
    "axisSide": "Más agradable",
    "emotions": ["cómodo", "contento", "satisfecho", "tranquilo", "relajado", "calmado", "sereno", "agradecido", "pleno", "seguro", "en paz", "descansado"]
  }
}
```

- [ ] **Step 2: Escribir el test del catálogo**

Crear `backend/tests/test_emotion_catalog.py`:

```python
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


def test_position_intensity_maps_to_1_10():
    assert position_intensity(0) == 1.0
    assert position_intensity(11) == 10.0
    assert 1.0 < position_intensity(5) < 10.0
```

- [ ] **Step 3: Verificar que el test falla**

Run: `cd backend && .venv/bin/python -m pytest tests/test_emotion_catalog.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.emotion_catalog'`

- [ ] **Step 4: Implementar `emotion_catalog.py`**

Crear `backend/services/emotion_catalog.py`:

```python
"""Catálogo de emociones — fuente única de la sub-matriz RULER.

Las 4 listas de 12 emociones (ordenadas de leve a intensa) son la base de:
- la sub-matriz del frontend (servida por GET /api/emotions),
- el cálculo de la intensidad emocional (posición -> intensidad, Task 2).
"""
import json
import os
import unicodedata

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "emotion_catalog.json")

with open(_PATH, encoding="utf-8") as _f:
    _CATALOG = json.load(_f)


def _norm(s: str) -> str:
    """Minúsculas y sin acentos, para emparejar nombres de emoción."""
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


# Índice nombre-normalizado -> posición 0-11 dentro de su cuadrante.
_POSITION = {}
for _q, _data in _CATALOG.items():
    for _i, _emo in enumerate(_data["emotions"]):
        _POSITION[_norm(_emo)] = _i


def get_catalog() -> dict:
    """El catálogo completo, tal cual, para servir al frontend."""
    return _CATALOG


def emotion_position(name: str):
    """Posición 0-11 de una emoción en su cuadrante, o None si no está."""
    return _POSITION.get(_norm(name))


def position_intensity(pos: int) -> float:
    """Mapea una posición 0-11 a una intensidad 1.0-10.0."""
    return 1.0 + pos * (9.0 / 11.0)
```

- [ ] **Step 5: Verificar que el test pasa**

Run: `cd backend && .venv/bin/python -m pytest tests/test_emotion_catalog.py -q`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/data/emotion_catalog.json backend/services/emotion_catalog.py backend/tests/test_emotion_catalog.py
git commit -m "feat(backend): catálogo de emociones unificado"
```

---

## Task 2: Intensidad dinámica 60/40

Crea `entry_feedback.py` con el cálculo de intensidad y helpers de contexto. Mejora el prompt de extracción RULER.

**Files:**
- Create: `backend/services/entry_feedback.py`
- Modify: `backend/prompts/ruler_extraction.txt:13`
- Test: `backend/tests/test_entry_feedback.py`

- [ ] **Step 1: Escribir los tests de intensidad y contexto**

Crear `backend/tests/test_entry_feedback.py`:

```python
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
```

- [ ] **Step 2: Verificar que el test falla**

Run: `cd backend && .venv/bin/python -m pytest tests/test_entry_feedback.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.entry_feedback'`

- [ ] **Step 3: Crear `entry_feedback.py` con intensidad y contexto**

Crear `backend/services/entry_feedback.py`:

```python
"""Feedback emocional contextual — se genera al registrar una emoción.

Reemplaza al reasoning_pipeline para el feedback de registro: aquí no hay
compuerta, el feedback se genera SIEMPRE en uno de dos modos (apoyo / ligero).
"""
from datetime import datetime

from services.emotion_catalog import emotion_position, position_intensity

# Pesos de la intensidad dinámica.
_W_EMOCION = 0.60
_W_CONTENIDO = 0.40
_W_PRIMARIA = 0.70
_W_SECUNDARIAS = 0.30

_CUADRANTES_NEGATIVOS = {"rojo", "azul"}
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ─── Intensidad dinámica ──────────────────────────────────────────────────

def _intensidad_emocion(selected_emotion, secundarias):
    """Intensidad 1-10 derivada de la posición de las emociones, o None."""
    pos = emotion_position(selected_emotion)
    if pos is None:
        return None
    primaria = position_intensity(pos)
    sec = []
    for s in secundarias or []:
        p = emotion_position(s)
        if p is not None:
            sec.append(position_intensity(p))
    if sec:
        return _W_PRIMARIA * primaria + _W_SECUNDARIAS * (sum(sec) / len(sec))
    return primaria


def compute_intensity(ruler: dict, selected_emotion: str) -> int:
    """Intensidad final 1-10: 60% emociones seleccionadas + 40% contenido."""
    contenido = min(max(float(ruler.get("intensidad") or 0), 1.0), 10.0)
    emocion = _intensidad_emocion(selected_emotion,
                                  ruler.get("emociones_secundarias"))
    if emocion is None:
        final = contenido
    else:
        final = _W_EMOCION * emocion + _W_CONTENIDO * contenido
    return min(max(round(final), 1), 10)


# ─── Contexto temporal ────────────────────────────────────────────────────

def franja_horaria(client_time):
    """(franja, día de la semana) a partir de un ISO 8601 con offset.

    Si `client_time` falta o es inválido, usa la hora local del servidor.
    """
    try:
        dt = datetime.fromisoformat(client_time)
    except (ValueError, TypeError):
        dt = datetime.now()
    h = dt.hour
    franja = ("madrugada" if h < 6 else "mañana" if h < 12
              else "tarde" if h < 19 else "noche")
    return franja, _DIAS[dt.weekday()]


# ─── Selección de modo ────────────────────────────────────────────────────

def select_mode(ruler: dict) -> str:
    """'apoyo' si la emoción es negativa e intensa; 'ligero' en otro caso."""
    cuad = (ruler.get("cuadrante") or "").strip().lower()
    intensidad = float(ruler.get("intensidad") or 0)
    if cuad in _CUADRANTES_NEGATIVOS and intensidad > 5:
        return "apoyo"
    return "ligero"
```

- [ ] **Step 4: Verificar que el test pasa**

Run: `cd backend && .venv/bin/python -m pytest tests/test_entry_feedback.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Mejorar el prompt de extracción RULER**

En `backend/prompts/ruler_extraction.txt`, reemplazar la línea 13:

```
  "intensidad": 1 a 10,
```

por:

```
  "intensidad": 1 a 10 (1=apenas perceptible, 4-5=notoria pero manejable, 7-8=fuerte y domina el momento, 10=desbordante; calíbrala por la severidad real del disparador y la fuerza de las palabras),
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/entry_feedback.py backend/prompts/ruler_extraction.txt backend/tests/test_entry_feedback.py
git commit -m "feat(backend): intensidad emocional dinámica 60/40"
```

---

## Task 3: Generación del feedback contextual

Completa `entry_feedback.py` con la generación por LLM en dos modos, el prompt nuevo, y el helper de ejemplos "que ayudaron".

**Files:**
- Modify: `backend/services/entry_feedback.py`
- Modify: `backend/services/memory_service.py`
- Create: `backend/prompts/entry_feedback.txt`
- Modify: `backend/tests/test_entry_feedback.py`

- [ ] **Step 1: Crear el prompt del feedback**

Crear `backend/prompts/entry_feedback.txt`:

```
Eres Mira, la compañera emocional de la app Mirror. Hablas como un espejo: cálida, cercana y serena.

Acabas de recibir el REGISTRO EMOCIONAL que la persona acaba de hacer, con EVIDENCIA estructurada. Tu tarea es escribir UN mensaje breve (1 a 2 frases, máximo 45 palabras) que la acompañe en este momento.

El registro viene en uno de dos MODOS:

MODO apoyo (emoción difícil e intensa):
- Valida lo que siente, sin minimizarlo.
- Ofrece 1 o 2 sugerencias sanas, éticas y realistas para sentirse un poco mejor.
- Apóyate en el contexto: la hora del día, sus disparadores recurrentes y, sobre todo, las "COSAS QUE YA LE HAN HECHO BIEN".

MODO ligero (emoción agradable, neutra, o difícil pero leve):
- Mensaje corto y luminoso.
- Reconoce o celebra el momento; si encaja, refuerza un hábito positivo.
- Puedes invitarle a continuar o a compartir algo de las "COSAS QUE YA LE HAN HECHO BIEN" (por ejemplo, compartir el momento con alguien importante).

REGLAS ABSOLUTAS:
- Usa ÚNICAMENTE la información de la evidencia. NUNCA inventes actividades, personas, lugares ni hechos.
- Si no hay "COSAS QUE YA LE HAN HECHO BIEN", NO inventes ninguna: acompaña con calidez y validación.
- No diagnostiques. No des consejos médicos ni psicológicos. No alarmes.
- Tono cercano y no invasivo: nada de "deberías". Prefiere "noté que…", "¿te ayudaría…?".
- Si la evidencia incluye "MENSAJES QUE ANTES LE AYUDARON", inspírate en su tono, no los copies.
- Responde en español. Sin markdown, sin listas, sin comillas. Solo el mensaje, nada más.
```

- [ ] **Step 2: Añadir los helpers de feedback a `memory_service.py`**

Al final de `backend/services/memory_service.py`, añadir:

```python
def get_helpful_feedback_examples(n: int = 2) -> list:
    """Mensajes de feedback que el usuario marcó como útiles, más recientes."""
    try:
        result = _collection.get(
            where={"feedback_reaccion": {"$eq": "me_ayudo"}},
            include=["metadatas"],
        )
    except Exception:  # noqa: BLE001 - los ejemplos son un extra, nunca crítico
        return []
    rows = []
    for meta in (result.get("metadatas") or []):
        msg = meta.get("feedback_mensaje")
        if msg:
            rows.append((meta.get("ts") or 0.0, msg))
    rows.sort(key=lambda r: r[0], reverse=True)
    return [m for _, m in rows[:n]]


def set_feedback_reaction(entry_id: str, reaccion: str) -> bool:
    """Actualiza `feedback_reaccion` en la metadata de una entrada guardada."""
    try:
        existing = _collection.get(ids=[entry_id], include=["metadatas"])
    except Exception:  # noqa: BLE001
        return False
    metas = existing.get("metadatas") or []
    if not metas or metas[0] is None:
        return False
    meta = dict(metas[0])
    meta["feedback_reaccion"] = reaccion
    try:
        _collection.update(ids=[entry_id], metadatas=[meta])
    except Exception:  # noqa: BLE001
        return False
    return True
```

- [ ] **Step 3: Escribir el test de generación de feedback**

Añadir a `backend/tests/test_entry_feedback.py`:

```python
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
    assert out["mensaje"]  # mensaje de respaldo, no vacío
```

- [ ] **Step 4: Verificar que el test falla**

Run: `cd backend && .venv/bin/python -m pytest tests/test_entry_feedback.py -q`
Expected: FAIL — `AttributeError: ... has no attribute 'generate_entry_feedback'`

- [ ] **Step 5: Añadir la generación de feedback a `entry_feedback.py`**

Añadir al final de `backend/services/entry_feedback.py`:

```python
# ─── Generación del feedback (LLM) ────────────────────────────────────────

_FALLBACK = ("Gracias por registrar cómo te sientes. "
             "Tomarte este momento ya es una forma de cuidarte.")


def _build_evidence(ruler: dict, modo: str, client_time) -> str:
    """Arma el bloque de evidencia estructurada para el prompt del feedback."""
    from services.memory_service import get_helpful_feedback_examples
    from services.profile_service import get_wellbeing_sources

    franja, dia = franja_horaria(client_time)
    lines = [
        f"MODO: {modo}",
        f"EMOCIÓN: {ruler.get('emocion_primaria', '?')} "
        f"(cuadrante {ruler.get('cuadrante', '?')}, "
        f"intensidad {ruler.get('intensidad', '?')}/10)",
    ]
    if ruler.get("disparador"):
        lines.append(f"DISPARADOR: {ruler['disparador']}")
    if ruler.get("resumen"):
        lines.append(f"RESUMEN: {ruler['resumen']}")
    lines.append(f"MOMENTO: {franja}, {dia}")

    try:
        fuentes = get_wellbeing_sources(5)
        conocidas = []
        for cat in ("actividades", "lugares", "personas"):
            conocidas.extend(fuentes.get(cat, []))
    except Exception:  # noqa: BLE001
        conocidas = []
    if conocidas:
        lines.append("COSAS QUE YA LE HAN HECHO BIEN (sugiere solo estas, "
                     "nunca inventes): " + "; ".join(conocidas))
    else:
        lines.append("COSAS QUE YA LE HAN HECHO BIEN: sin datos — no "
                     "recomiendes actividades, solo acompaña con calidez.")

    try:
        ejemplos = get_helpful_feedback_examples(2)
    except Exception:  # noqa: BLE001
        ejemplos = []
    if ejemplos:
        lines.append("MENSAJES QUE ANTES LE AYUDARON (inspírate en su tono):")
        for m in ejemplos:
            lines.append(f"- {m}")
    return "\n".join(lines)


def generate_entry_feedback(ruler: dict, selected_emotion: str,
                            client_time) -> dict:
    """Genera el feedback contextual de Mira para una entrada recién analizada.

    Devuelve {'mensaje': str, 'modo': 'apoyo'|'ligero'}. Nunca lanza: ante
    cualquier fallo del LLM devuelve un mensaje de respaldo cálido.
    """
    modo = select_mode(ruler)
    try:
        from services.llm_service import _load_prompt, _ollama_generate
        system = _load_prompt("entry_feedback.txt")
        evidence = _build_evidence(ruler, modo, client_time)
        mensaje = _ollama_generate(system, evidence, temperature=0.7,
                                   num_predict=180).strip()
        if not mensaje:
            mensaje = _FALLBACK
    except Exception:  # noqa: BLE001 - el feedback nunca debe romper el análisis
        mensaje = _FALLBACK
    return {"mensaje": mensaje, "modo": modo}
```

- [ ] **Step 6: Verificar que el test pasa**

Run: `cd backend && .venv/bin/python -m pytest tests/test_entry_feedback.py -q`
Expected: PASS (10 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/services/entry_feedback.py backend/services/memory_service.py backend/prompts/entry_feedback.txt backend/tests/test_entry_feedback.py
git commit -m "feat(backend): generación de feedback contextual en dos modos"
```

---

## Task 4: Endpoints de emoción

Rehace `/api/analyze`, `/api/entry`, `/api/save`; añade `/api/feedback/reaction` y `GET /api/emotions`. Actualiza los tests del route.

**Files:**
- Modify: `backend/routes/emotion.py`
- Test: `backend/tests/test_emotion_route.py`

- [ ] **Step 1: Reescribir `emotion.py`**

Reemplazar **todo** el contenido de `backend/routes/emotion.py` con:

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
import tempfile, os
from logging_config import get_logger
from services.llm_service import extract_ruler
from services.memory_service import save_entry, set_feedback_reaction
from services.emotion_catalog import get_catalog
from services.entry_feedback import compute_intensity, generate_entry_feedback
from services.audio_errors import AudioError
from crisis_keywords import contains_crisis

router = APIRouter()
_log = get_logger("entry")


def _update_profile(ruler: dict, background: BackgroundTasks) -> None:
    """Integra la entrada en el perfil consolidado. Nunca rompe el guardado."""
    try:
        from services.profile_service import (
            regenerate_narrative,
            should_regenerate_narrative,
            update_profile_with_entry,
        )
        p = update_profile_with_entry(ruler)
        if should_regenerate_narrative(p):
            background.add_task(regenerate_narrative)
    except Exception as exc:  # noqa: BLE001 - el perfil es un derivado, no crítico
        _log.warning("No se pudo actualizar el perfil: %s", exc)


def _analyze(full_text: str, emocion_seleccionada: str, client_time) -> dict:
    """Extrae RULER, calcula intensidad y genera el feedback. No guarda."""
    ruler = extract_ruler(full_text)
    ruler["emocion_seleccionada"] = emocion_seleccionada
    ruler["crisis_flag"] = contains_crisis(full_text)
    ruler["intensidad"] = compute_intensity(ruler, emocion_seleccionada)
    if client_time:
        ruler["client_time"] = client_time
    ruler["feedback"] = generate_entry_feedback(ruler, emocion_seleccionada,
                                                client_time)
    return ruler


class AnalyzeRequest(BaseModel):
    text: str
    emocion_seleccionada: str
    client_time: str | None = None


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    full_text = f"Emoción seleccionada: {req.emocion_seleccionada}. {req.text}"
    ruler = _analyze(full_text, req.emocion_seleccionada, req.client_time)
    ruler["transcripcion"] = req.text
    return ruler


@router.get("/emotions")
async def emotions():
    """Catálogo unificado de emociones — fuente única de la sub-matriz."""
    return get_catalog()


class ReactionRequest(BaseModel):
    entry_id: str
    reaccion: str


@router.post("/feedback/reaction")
async def feedback_reaction(req: ReactionRequest):
    """Registra si el feedback de la IA le ayudó al usuario."""
    return {"ok": set_feedback_reaction(req.entry_id, req.reaccion)}


@router.post("/save")
async def save(ruler: dict, background: BackgroundTasks):
    # El feedback y la reacción se aplanan a metadata escalar de ChromaDB.
    reaccion = ruler.pop("reaccion_feedback", None)
    fb = ruler.pop("feedback", None) or {}
    ruler["feedback_mensaje"] = fb.get("mensaje", "")
    ruler["feedback_modo"] = fb.get("modo", "")
    ruler["feedback_reaccion"] = reaccion or ""
    entry_id, saved_at = save_entry(ruler)
    ruler["saved_at"] = saved_at
    _update_profile(ruler, background)
    return {"id": entry_id, "saved_at": saved_at}


@router.post("/entry")
async def entry(
    audio: UploadFile = File(...),
    emocion_seleccionada: str = Form(...),
    client_time: str = Form(None),
):
    _log.info("Nueva entrada — emoción seleccionada: %s", emocion_seleccionada)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        data = await audio.read()
        tmp.write(data)
        tmp_path = tmp.name
    _log.debug("Audio recibido: %d bytes", len(data))
    try:
        from services.audio_pipeline import transcribe_audio

        transcription = transcribe_audio(tmp_path)
        full_text = f"Emoción seleccionada: {emocion_seleccionada}. {transcription['text']}"
        _log.info("Extrayendo RULER con el LLM…")
        ruler = _analyze(full_text, emocion_seleccionada, client_time)
        ruler["transcripcion"] = transcription["text"]
        if ruler["crisis_flag"]:
            _log.warning("crisis_flag activado en esta entrada")
        return ruler
    except AudioError as exc:
        _log.warning("Error de audio: %s", exc)
        raise HTTPException(exc.status_code, str(exc) or exc.detail)
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 2: Reescribir los tests del route**

Reemplazar **todo** el contenido de `backend/tests/test_emotion_route.py` con:

```python
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
```

- [ ] **Step 3: Verificar los tests del route**

Run: `cd backend && .venv/bin/python -m pytest tests/test_emotion_route.py -q`
Expected: PASS (5 passed)

- [ ] **Step 4: Verificar que la suite completa sigue verde**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: PASS — sin fallos (las pruebas de audio/stt siguen pasando).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/emotion.py backend/tests/test_emotion_route.py
git commit -m "feat(backend): endpoints de análisis con feedback, intensidad y catálogo"
```

---

## Task 5: Retirar el pipeline de razonamiento y el endpoint companion

Mueve `classify_state` a `signals_engine.py`, elimina `reasoning_pipeline.py` y `routes/companion.py`, y limpia `main.py`.

**Files:**
- Modify: `backend/services/signals_engine.py`
- Modify: `backend/routes/history.py`
- Modify: `backend/main.py`
- Delete: `backend/services/reasoning_pipeline.py`
- Delete: `backend/routes/companion.py`
- Test: `backend/tests/test_signals_engine.py`

- [ ] **Step 1: Mover `classify_state` a `signals_engine.py`**

Al final de `backend/services/signals_engine.py`, añadir:

```python
def classify_state(signals: list) -> str:
    """Clasifica el estado emocional a partir de las señales detectadas.

    Devuelve: en_dificultad | volatil | en_mejora | desconectado | estable.
    """
    tipos = {s.tipo for s in signals}
    if "emocion_negativa_intensa" in tipos or "racha_negativa" in tipos:
        return "en_dificultad"
    if "intensidad_anomala" in tipos:
        return "volatil"
    if "tendencia_valencia" in tipos:
        t = next(s for s in signals if s.tipo == "tendencia_valencia")
        return "en_mejora" if t.evidencia.get("delta", 0) > 0 else "en_dificultad"
    if "ausencia_registro" in tipos:
        return "desconectado"
    return "estable"
```

- [ ] **Step 2: Escribir el test de `classify_state`**

Crear `backend/tests/test_signals_engine.py`:

```python
from services.signals_engine import Signal, classify_state


def test_classify_state_estable_sin_senales():
    assert classify_state([]) == "estable"


def test_classify_state_en_dificultad():
    s = Signal(tipo="emocion_negativa_intensa", titulo="x")
    assert classify_state([s]) == "en_dificultad"


def test_classify_state_volatil():
    s = Signal(tipo="intensidad_anomala", titulo="x")
    assert classify_state([s]) == "volatil"
```

- [ ] **Step 3: Verificar el test**

Run: `cd backend && .venv/bin/python -m pytest tests/test_signals_engine.py -q`
Expected: PASS (3 passed)

- [ ] **Step 4: Actualizar el import en `history.py`**

En `backend/routes/history.py`, línea 28, reemplazar:

```python
        from services.reasoning_pipeline import classify_state
```

por:

```python
        from services.signals_engine import classify_state
```

- [ ] **Step 5: Eliminar el pipeline y el route companion**

```bash
git rm backend/services/reasoning_pipeline.py backend/routes/companion.py
```

- [ ] **Step 6: Limpiar `main.py`**

En `backend/main.py`, línea 16, reemplazar:

```python
from routes import audio, emotion, history, chat, companion
```

por:

```python
from routes import audio, emotion, history, chat
```

Y eliminar la línea 73 completa:

```python
app.include_router(companion.router, prefix="/api")
```

- [ ] **Step 7: Verificar que nada quedó colgado**

Run: `cd backend && grep -rn "reasoning_pipeline\|companion" --include="*.py" .`
Expected: Sin resultados (ninguna referencia restante).

Run: `cd backend && .venv/bin/python -c "import main"`
Expected: Sin errores de import.

- [ ] **Step 8: Verificar la suite completa**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: PASS — sin fallos.

- [ ] **Step 9: Commit**

```bash
git add backend/services/signals_engine.py backend/routes/history.py backend/main.py backend/tests/test_signals_engine.py
git commit -m "refactor(backend): retirar reasoning_pipeline y endpoint companion"
```

---

## Task 6: Frontend — catálogo dinámico y plumbing

El frontend obtiene el catálogo de `GET /api/emotions`, elimina el `QUADRANTS` hardcodeado, envía `client_time` y cachea el catálogo en el service worker.

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/index.html`
- Modify: `frontend/styles.css`
- Modify: `frontend/sw.js`

- [ ] **Step 1: Reemplazar el bloque `QUADRANTS` por una variable vacía**

En `frontend/app.js`, reemplazar el bloque `RULER DATA` completo (líneas 4-30, desde `// ─── RULER DATA` hasta el `};` que cierra `QUADRANTS`) por:

```javascript
// ─── RULER DATA ───────────────────────────────────────────────────────────────
// El catálogo es la fuente única del backend; se obtiene de GET /api/emotions.
let QUADRANTS = null;
```

- [ ] **Step 2: Añadir el helper de hora local y `loadCatalog`**

En `frontend/app.js`, justo después del bloque `STATE` (después de la llave de cierre de `let state = {...}`), añadir:

```javascript
// ─── HORA LOCAL ───────────────────────────────────────────────────────────────
// ISO 8601 con offset local (ej. 2026-05-17T21:34:00-06:00).
function localISOTime() {
  const d = new Date();
  const off = -d.getTimezoneOffset(); // minutos respecto a UTC
  const sign = off >= 0 ? "+" : "-";
  const pad = n => String(Math.floor(Math.abs(n))).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate())
    + "T" + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds())
    + sign + pad(off / 60) + ":" + pad(off % 60);
}

// ─── CATÁLOGO DE EMOCIONES ─────────────────────────────────────────────────────
async function loadCatalog() {
  document.getElementById("app-error").classList.add("hidden");
  try {
    const res = await fetch(`${API}/api/emotions`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    QUADRANTS = await res.json();
  } catch (err) {
    console.error("No se pudo cargar el catálogo de emociones", err);
    document.getElementById("app-error").classList.remove("hidden");
  }
}
```

- [ ] **Step 3: Proteger el tap de cuadrante hasta que el catálogo esté listo**

En `frontend/app.js`, dentro del handler de click de `.quadrant` (función `q.addEventListener("click", ...)`), añadir como primera línea del callback:

```javascript
    if (!QUADRANTS) { loadCatalog(); return; }
```

- [ ] **Step 4: Enviar `client_time` en las llamadas de análisis**

En `frontend/app.js`, en `analyzeText`, reemplazar el `fetch` de `/api/analyze` (el objeto `body`) para que el cuerpo sea:

```javascript
      body: JSON.stringify({
        text: text,
        emocion_seleccionada: state.selectedEmotion,
        client_time: localISOTime(),
      }),
```

Y eliminar la línea `const fullText = ...` y el uso de `fullText` (ahora se manda `text` crudo; el backend antepone la emoción).

En `analyzeEntry`, después de `form.append("emocion_seleccionada", state.selectedEmotion);`, añadir:

```javascript
  form.append("client_time", localISOTime());
```

- [ ] **Step 5: Reemplazar `loadHomeCompanion()` al arranque**

En `frontend/app.js`, en el bloque `ARRANQUE` del final, reemplazar la línea `loadHomeCompanion();` por:

```javascript
loadCatalog();
```

- [ ] **Step 6: Añadir el overlay de error en `index.html`**

En `frontend/index.html`, eliminar la línea `<div id="home-companion" class="hidden"></div>` (línea 29). Justo antes de `<script src="/app.js"></script>`, añadir:

```html
  <!-- ─── Error de arranque (catálogo no disponible) ─────────────────────── -->
  <div id="app-error" class="app-error hidden">
    <p>No se pudo cargar Mirror. Revisa tu conexión.</p>
    <button id="btn-app-retry" class="btn-primary" type="button">Reintentar</button>
  </div>
```

- [ ] **Step 7: Cablear el botón de reintento**

En `frontend/app.js`, en el bloque `ARRANQUE`, añadir antes de `loadCatalog();`:

```javascript
document.getElementById("btn-app-retry").addEventListener("click", loadCatalog);
```

- [ ] **Step 8: Estilos del overlay de error**

Al final de `frontend/styles.css`, añadir:

```css
/* ─── Error de arranque ─────────────────────────────────────────────── */
.app-error {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 32px;
  background: var(--bg);
  text-align: center;
  color: var(--text-dim);
}
.app-error .btn-primary { max-width: 240px; }
```

- [ ] **Step 9: Cachear `/api/emotions` en el service worker**

Reemplazar **todo** el contenido de `frontend/sw.js` con:

```javascript
const CACHE = "mirror-v5";
const ASSETS = ["/", "/app.js", "/styles.css", "/tailwind.css", "/assets/mira.png"];

// Precarga tolerante: un asset ausente no aborta la instalación del SW.
self.addEventListener("install", e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(c => Promise.allSettled(ASSETS.map(a => c.add(a))))
  );
});

// Limpia versiones de caché anteriores para que un deploy se vea de inmediato.
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = e.request.url;
  // El catálogo de emociones SÍ se cachea: red primero, caché como respaldo offline.
  if (url.includes("/api/emotions")) {
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  if (url.includes("/api/")) return; // el resto de la API nunca se cachea
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
```

- [ ] **Step 10: Verificar sintaxis y navegador**

Run: `node --check frontend/app.js`
Expected: Sin salida (sintaxis válida).

Verificación en navegador (con el backend corriendo): abrir la app, confirmar que el Mood Meter funciona, tocar un cuadrante y ver la sub-matriz con las 12 emociones. En DevTools → Network, confirmar la llamada a `/api/emotions`.

- [ ] **Step 11: Commit**

```bash
git add frontend/app.js frontend/index.html frontend/styles.css frontend/sw.js
git commit -m "feat(frontend): catálogo dinámico, hora local y caché del SW"
```

---

## Task 7: Botón de grabación tap / hold

Rehace la máquina de estados de grabación: arregla la condición de carrera con `getUserMedia` y garantiza que el micrófono se libere en toda salida.

**Files:**
- Modify: `frontend/app.js`

- [ ] **Step 1: Reemplazar las variables de estado de grabación**

En `frontend/app.js`, reemplazar el bloque de variables (desde `let mediaRecorder = null;` hasta `let recordTimerInterval = null;`, líneas ~116-125) por:

```javascript
let mediaRecorder = null;
let audioChunks = [];
let animFrame = null;
let analyser = null;
let audioStream = null;
let audioCtx = null;
let recordStartTime = 0;
let recordTimerInterval = null;
// Máquina de estados: idle | arming (pidiendo micrófono) | recording | stopping
let recState = "idle";
let recMode = null;          // "hold" | "toggle" — cómo terminará la grabación
let pressStartTs = 0;
let stopWhenReady = false;   // el gesto "hold" terminó mientras se pedía el micrófono
```

- [ ] **Step 2: Reemplazar `cancelRecording`**

Reemplazar la función `cancelRecording` completa por:

```javascript
function cancelRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.onstop = () => releaseAudioResources();
    mediaRecorder.stop();
  } else {
    releaseAudioResources();
  }
  cancelAnimationFrame(animFrame);
  stopRecordTimer();
  recState = "idle";
  recMode = null;
  stopWhenReady = false;
  audioChunks = [];
  recordBtn.classList.remove("recording", "toggle");
  btnCancelRecord.classList.add("hidden");
  recordStatus.textContent = "Toca o mantén presionado para hablar";
}
```

- [ ] **Step 3: Reemplazar los handlers de puntero/teclado y `startRecording`/`finishRecording`**

Reemplazar todo el bloque desde `recordBtn.addEventListener("pointerdown", ...)` hasta el final de la función `releaseAudioResources` (líneas ~223-347) por:

```javascript
recordBtn.addEventListener("pointerdown", e => {
  // setPointerCapture: el botón conserva el pointerup aunque el dedo se deslice fuera.
  try { recordBtn.setPointerCapture(e.pointerId); } catch {}
  // Si ya graba en modo manos libres, este toque la finaliza.
  if (recState === "recording" && recMode === "toggle") {
    finishRecording();
    return;
  }
  if (recState !== "idle") return; // ignora gestos mientras arma/detiene
  pressStartTs = Date.now();
  recMode = "hold";                // por defecto; pointerup puede pasarlo a "toggle"
  stopWhenReady = false;
  beginRecording();
});

recordBtn.addEventListener("pointerup", () => {
  if (recMode !== "hold") return;  // ya pasó a toggle, o no hay gesto activo
  const held = Date.now() - pressStartTs;
  if (held < TAP_THRESHOLD_MS) {
    // Toque corto → modo manos libres: sigue grabando hasta el próximo toque.
    recMode = "toggle";
    if (recState === "recording") {
      recordBtn.classList.add("toggle");
      recordStatus.textContent = "Grabando… toca para terminar";
    }
    // Si aún está en "arming", beginRecording verá recMode === "toggle" y continuará.
  } else if (recState === "recording") {
    finishRecording();             // se mantuvo presionado → termina al soltar
  } else {
    stopWhenReady = true;          // soltó durante "arming" → terminar al estar listo
  }
});

recordBtn.addEventListener("pointercancel", () => {
  if (recMode === "hold") {
    if (recState === "recording") finishRecording();
    else stopWhenReady = true;
  }
});

// Soporte de teclado: Enter/Espacio alterna la grabación (modo manos libres).
recordBtn.addEventListener("click", e => {
  if (e.detail !== 0) return; // ignora el click sintético que sigue al pointer
  if (recState === "recording") {
    finishRecording();
  } else if (recState === "idle") {
    recMode = "toggle";
    stopWhenReady = false;
    beginRecording();
  }
});

async function beginRecording() {
  recState = "arming";
  if (!navigator.mediaDevices?.getUserMedia) {
    recordStatus.textContent = "La grabación necesita HTTPS o localhost.";
    recState = "idle";
    recMode = null;
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    recordStatus.textContent = "No se pudo acceder al micrófono. Revisa los permisos.";
    console.error(err);
    recState = "idle";
    recMode = null;
    return;
  }
  // El gesto fue un "hold" demasiado corto que terminó mientras se pedía el
  // permiso: descartar el stream sin grabar nada.
  if (stopWhenReady && recMode === "hold") {
    stream.getTracks().forEach(t => t.stop());
    recState = "idle";
    recMode = null;
    stopWhenReady = false;
    recordStatus.textContent = "Toca o mantén presionado para hablar";
    return;
  }

  audioStream = stream;
  audioCtx = new AudioContext();
  const source = audioCtx.createMediaStreamSource(audioStream);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  source.connect(analyser);

  audioChunks = [];
  mediaRecorder = new MediaRecorder(audioStream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.start();
  recordStartTime = Date.now();
  recState = "recording";

  recordBtn.classList.add("recording");
  if (recMode === "toggle") {
    recordBtn.classList.add("toggle");
    recordStatus.textContent = "Grabando… toca para terminar";
  } else {
    recordStatus.textContent = "Grabando…";
  }
  btnCancelRecord.classList.remove("hidden");
  startRecordTimer();
  resizeWaveCanvas();
  drawWaveform();

  // Si mientras se pedía el micrófono el usuario ya soltó un "hold" largo.
  if (stopWhenReady) finishRecording();
}

function finishRecording() {
  if (recState !== "recording" || !mediaRecorder) return;
  const elapsed = Date.now() - recordStartTime;
  recState = "stopping";
  recMode = null;
  stopWhenReady = false;
  recordBtn.classList.remove("recording", "toggle");
  stopRecordTimer();
  btnCancelRecord.classList.add("hidden");
  cancelAnimationFrame(animFrame);

  mediaRecorder.onstop = () => {
    releaseAudioResources();
    recState = "idle";
    if (elapsed < MIN_RECORDING_MS) {
      recordStatus.textContent = "Mantén presionado o toca para grabar un poco más.";
      return;
    }
    analyzeEntry(new Blob(audioChunks, { type: "audio/webm" }));
  };
  mediaRecorder.stop();
}

// Libera el micrófono y el AudioContext — sin esto el indicador de micrófono
// queda encendido y el navegador deja de crear AudioContext tras varias grabaciones.
function releaseAudioResources() {
  if (audioStream) {
    audioStream.getTracks().forEach(t => t.stop());
    audioStream = null;
  }
  if (audioCtx && audioCtx.state !== "closed") {
    audioCtx.close();
    audioCtx = null;
  }
  analyser = null;
  mediaRecorder = null;
}
```

- [ ] **Step 4: Actualizar `resetRecordState`**

En `frontend/app.js`, en `resetRecordState`, reemplazar la línea `toggleMode = false;` por:

```javascript
  recState = "idle";
  recMode = null;
  stopWhenReady = false;
```

- [ ] **Step 5: Verificar sintaxis y navegador**

Run: `node --check frontend/app.js`
Expected: Sin salida.

Verificación en navegador: ir a Grabar. Probar (a) **tap** corto → empieza a grabar, el botón muestra "toca para terminar"; otro tap → procesa. (b) **hold** ≥1s → graba; soltar → procesa. (c) Cancelar mientras graba. En DevTools, confirmar que tras cada caso el indicador de micrófono se apaga (no quedan `MediaStreamTrack` activos).

- [ ] **Step 6: Commit**

```bash
git add frontend/app.js
git commit -m "fix(frontend): rehacer la máquina de estados de grabación tap/hold"
```

---

## Task 8: Transición orgánica del Mood Meter

El cuadrante tocado se expande hasta llenar la pantalla, los demás se desvanecen, y las 12 emociones emergen escalonadas desde el centro.

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`

- [ ] **Step 1: Ajustar el timing del tap de cuadrante**

En `frontend/app.js`, en el handler de click de `.quadrant`, cambiar el valor del `setTimeout` de `260` a `380` (el `setTimeout(() => { ... }, 260)` pasa a `}, 380)`).

- [ ] **Step 2: Stagger radial de las emociones en `renderSubmatrix`**

En `frontend/app.js`, dentro de `renderSubmatrix`, reemplazar la línea:

```javascript
    tile.style.animationDelay = `${idx * 0.03}s`;
```

por:

```javascript
    // Emergen desde el centro de la rejilla 3x4: el delay crece con la distancia.
    const row = Math.floor(idx / 3), col = idx % 3;
    const dist = Math.hypot(row - 1.5, col - 1);
    tile.style.animationDelay = `${0.04 + dist * 0.05}s`;
```

- [ ] **Step 3: Reemplazar el CSS de la transición de zoom**

En `frontend/styles.css`, reemplazar el bloque "Zoom del cuadrante" (desde `/* Zoom del cuadrante al entrar a la sub-matriz */` hasta la regla `@keyframes submatrixIn { ... }` incluida) por:

```css
/* Transición orgánica cuadrante → sub-matriz */
.mood-meter.dimmed .quadrant:not(.zooming) {
  opacity: 0;
  transform: scale(0.4);
}
.mood-meter.dimmed .quadrant {
  transition: transform 0.34s var(--ease-soft), opacity 0.3s ease;
}
.quadrant.zooming {
  transform: scale(2.7);
  opacity: 0;
  z-index: 2;
  transition: transform 0.42s var(--ease-soft), opacity 0.42s ease 0.06s;
}
#screen-words.active { animation: screenIn 0.3s var(--ease-soft) both; }

/* Las emociones emergen escalonadas desde el centro */
.sub-emotion {
  animation: tileEmerge 0.5s var(--ease-spring) both;
}
@keyframes tileEmerge {
  from { opacity: 0; transform: scale(0.55); }
  to   { opacity: 1; transform: scale(1); }
}
```

- [ ] **Step 4: Aparición sutil de las etiquetas de eje**

En `frontend/styles.css`, justo después del bloque anterior, añadir:

```css
/* Las etiquetas de eje y el subtítulo aparecen al final, sutiles */
#screen-words .submatrix-axis,
#screen-words .submatrix-sub {
  animation: axisFade 0.5s var(--ease-soft) 0.34s both;
}
@keyframes axisFade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
```

- [ ] **Step 5: Verificar sintaxis y navegador**

Run: `node --check frontend/app.js`
Expected: Sin salida.

Verificación en navegador: tocar cada uno de los 4 cuadrantes y observar que (a) el cuadrante crece y se desvanece, los otros 3 se encogen y se van; (b) las 12 emociones aparecen escalonadas desde el centro; (c) las etiquetas de eje entran después. Activar `prefers-reduced-motion` en DevTools (Rendering → Emulate CSS media) y confirmar que la navegación sigue funcionando sin animación.

- [ ] **Step 6: Commit**

```bash
git add frontend/app.js frontend/styles.css
git commit -m "feat(frontend): transición orgánica del Mood Meter a la sub-matriz"
```

---

## Task 9: Animación de carga "Mira reflexionando"

Elimina el anillo giratorio y lo reemplaza por un aura de anillos concéntricos que respiran, con el color del cuadrante elegido.

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`

- [ ] **Step 1: Añadir los anillos del aura en `index.html`**

En `frontend/index.html`, dentro de `<div class="mascota-orb">` (en `#screen-analyzing`), justo después de la etiqueta de apertura `<div class="mascota-orb">`, añadir las tres líneas:

```html
        <span class="orb-ring" aria-hidden="true"></span>
        <span class="orb-ring" aria-hidden="true"></span>
        <span class="orb-ring" aria-hidden="true"></span>
```

- [ ] **Step 2: Teñir el orbe con el color del cuadrante**

En `frontend/app.js`, al inicio de la función `analyzeEntry` y al inicio de `analyzeText`, justo después de `showScreen("analyzing");` (en `analyzeText`) y antes de construир el `FormData` (en `analyzeEntry`, después de `showScreen("analyzing");`), añadir esta línea en **ambas** funciones:

```javascript
  setOrbColor(state.selectedQuadrant);
```

Y añadir la función `setOrbColor` justo antes de `function startAnalyzingCopy()`:

```javascript
// Tiñe el aura de carga con el color del cuadrante elegido.
function setOrbColor(quadrant) {
  const colors = { rojo: "#C2553B", amarillo: "#B0852A", azul: "#4E6E88", verde: "#557A58" };
  document.getElementById("screen-analyzing")
    .style.setProperty("--orb-color", colors[quadrant] || "#7D72D6");
}
```

- [ ] **Step 3: Reemplazar el CSS del orbe**

En `frontend/styles.css`, reemplazar la regla `.mascota-orb::before { ... }` completa por:

```css
.mascota-orb::before {
  content: '';
  position: absolute;
  inset: 28px;
  border-radius: 50%;
  background: radial-gradient(circle,
    color-mix(in srgb, var(--orb-color, var(--indigo-light)) 32%, transparent) 0%,
    transparent 70%);
  animation: glowPulse 3.4s var(--ease-soft) infinite;
}

/* Aura: anillos concéntricos que respiran hacia afuera */
.orb-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1.5px solid var(--orb-color, var(--indigo-light));
  opacity: 0;
  animation: orbBreathe 3.6s var(--ease-soft) infinite;
}
.orb-ring:nth-of-type(2) { animation-delay: 1.2s; }
.orb-ring:nth-of-type(3) { animation-delay: 2.4s; }
@keyframes orbBreathe {
  0%   { opacity: 0;    transform: scale(0.68); }
  30%  { opacity: 0.45; }
  100% { opacity: 0;    transform: scale(1.28); }
}
```

- [ ] **Step 4: Eliminar el anillo giratorio**

En `frontend/styles.css`, eliminar por completo el bloque "Anillo de progreso del orbe de análisis" (el comentario y la regla `.mascota-orb::after { ... }`, líneas ~1142-1153).

En el bloque `@media (prefers-reduced-motion: reduce)`, eliminar las dos líneas del override del orbe:

```css
  /* El anillo del orbe también puede girar (comunica "procesando") */
  .mascota-orb::after { animation: spin 1.6s linear infinite !important; }
```

Eliminar también la regla `@keyframes spin { to { transform: rotate(360deg); } }` (línea ~1033) — ya no se usa.

- [ ] **Step 5: Teñir las partículas con el color del orbe**

En `frontend/styles.css`, en la regla `.orb-spark`, reemplazar:

```css
  background: var(--indigo-light);
  box-shadow: 0 0 12px 2px rgba(125, 114, 214, 0.7);
```

por:

```css
  background: var(--orb-color, var(--indigo-light));
  box-shadow: 0 0 12px 2px color-mix(in srgb, var(--orb-color, var(--indigo-light)) 70%, transparent);
```

- [ ] **Step 6: Verificar sintaxis y navegador**

Run: `node --check frontend/app.js`
Expected: Sin salida.

Verificación en navegador: registrar una emoción de cada cuadrante y observar la pantalla de análisis — el aura debe respirar con anillos concéntricos del color del cuadrante, sin ningún anillo girando. Confirmar con `prefers-reduced-motion` que no hay movimiento brusco.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat(frontend): aura de carga que respira en lugar del anillo giratorio"
```

---

## Task 10: Bottom drawer reutilizable + historial clicable

Componente de hoja inferior que anima de abajo hacia arriba. Las tarjetas del historial se vuelven clicables y lo abren con el detalle RULER.

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`

- [ ] **Step 1: Añadir el marcado del drawer en `index.html`**

En `frontend/index.html`, justo antes del `<nav id="tab-bar" ...>`, añadir:

```html
  <!-- ─── Bottom drawer reutilizable ─────────────────────────────────────── -->
  <div id="drawer" class="drawer" aria-hidden="true">
    <div class="drawer-backdrop"></div>
    <div class="drawer-sheet" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <button class="drawer-handle" id="drawer-close" type="button" aria-label="Cerrar"></button>
      <h3 id="drawer-title"></h3>
      <div id="drawer-content"></div>
    </div>
  </div>
```

- [ ] **Step 2: Añadir el componente drawer y `rulerDetailHTML` en `app.js`**

En `frontend/app.js`, justo antes del bloque `// ─── CRISIS MODAL`, añadir:

```javascript
// ─── BOTTOM DRAWER ────────────────────────────────────────────────────────────
let drawerLastFocus = null;
let drawerDragStartY = 0;

const drawerEl = document.getElementById("drawer");
const drawerSheet = drawerEl.querySelector(".drawer-sheet");

function openDrawer(title, contentHTML) {
  document.getElementById("drawer-title").textContent = title;
  document.getElementById("drawer-content").innerHTML = contentHTML;
  drawerLastFocus = document.activeElement;
  drawerEl.classList.add("open");
  drawerEl.setAttribute("aria-hidden", "false");
  if (window.lucide) lucide.createIcons();
  document.getElementById("drawer-close").focus();
  document.addEventListener("keydown", onDrawerKeydown);
}

function closeDrawer() {
  drawerEl.classList.remove("open");
  drawerEl.setAttribute("aria-hidden", "true");
  document.removeEventListener("keydown", onDrawerKeydown);
  if (drawerLastFocus && typeof drawerLastFocus.focus === "function") drawerLastFocus.focus();
}

function onDrawerKeydown(e) {
  if (e.key === "Escape") closeDrawer();
}

drawerEl.querySelector(".drawer-backdrop").addEventListener("click", closeDrawer);
document.getElementById("drawer-close").addEventListener("click", closeDrawer);

// Arrastrar la hoja hacia abajo para cerrarla.
drawerSheet.addEventListener("pointerdown", e => {
  if (e.target.closest("#drawer-content")) return; // no interferir con el scroll
  drawerDragStartY = e.clientY;
  drawerSheet.setPointerCapture(e.pointerId);
});
drawerSheet.addEventListener("pointerup", e => {
  if (drawerDragStartY && e.clientY - drawerDragStartY > 80) closeDrawer();
  drawerDragStartY = 0;
});

/** HTML del desglose RULER de una entrada — reusable en resultados e historial. */
function rulerDetailHTML(ruler) {
  const colorMap = { rojo: "q-rojo", amarillo: "q-amarillo", azul: "q-azul", verde: "q-verde" };
  const sec = ruler.emociones_secundarias;
  const secArr = Array.isArray(sec) ? sec : (sec ? [sec] : []);
  const pens = Array.isArray(ruler.pensamientos) ? ruler.pensamientos : [];
  return `
    <div class="info-card">
      <p class="info-label">Emoción principal</p>
      <p class="text-lg font-bold ${colorMap[ruler.cuadrante] || ''}">${ruler.emocion_primaria || "—"}</p>
      ${secArr.length ? `<p class="text-xs t-dim mt-1">${secArr.join(", ")}</p>` : ""}
    </div>
    <div class="info-card">
      <p class="info-label">Disparador</p>
      <p class="text-sm t-strong">${ruler.disparador || "—"}</p>
    </div>
    <div class="info-card">
      <p class="info-label">Intensidad</p>
      <div class="flex gap-1 mt-1">
        ${Array.from({ length: 10 }, (_, i) => `<div class="h-2 flex-1 rounded-full ${i < (ruler.intensidad || 0) ? "bg-indigo-500" : "track"}"></div>`).join("")}
      </div>
    </div>
    <div class="info-card">
      <p class="info-label">Resumen</p>
      <p class="text-sm t-soft italic">${ruler.resumen || "—"}</p>
    </div>
    ${pens.length ? `<div class="info-card"><p class="info-label mb-2">Pensamientos</p>${pens.map(t => `<p class="text-sm t-soft">• ${t}</p>`).join("")}</div>` : ""}
  `;
}
```

- [ ] **Step 3: Hacer clicables las tarjetas del historial**

En `frontend/app.js`, en `loadHistory`, reemplazar la construcción de cada tarjeta para que sea un `<button>` con datos. Reemplazar el `container.innerHTML = data.entries.map(...)` por:

```javascript
    container.removeAttribute("aria-busy");
    container.innerHTML = data.entries.map((e, i) => `
      <button type="button" class="entry-card ${e.cuadrante || 'azul'}" data-idx="${i}">
        <div class="flex justify-between items-start">
          <div>
            <span class="font-medium t-strong">${e.emocion_primaria || "—"}</span>
            ${e.emociones_secundarias ? `<span class="text-xs t-dim ml-2">${Array.isArray(e.emociones_secundarias) ? e.emociones_secundarias.join(", ") : e.emociones_secundarias}</span>` : ""}
          </div>
          <span class="text-xs t-dim">${formatDate(e.saved_at)}</span>
        </div>
        <p class="text-sm t-dim mt-1">${e.resumen || ""}</p>
        ${e.disparador ? `<p class="text-xs t-faint mt-1">↳ ${e.disparador}</p>` : ""}
      </button>
    `).join("");
    container.querySelectorAll(".entry-card").forEach(card => {
      card.addEventListener("click", () => {
        const entry = data.entries[Number(card.dataset.idx)];
        const fb = entry.feedback_mensaje
          ? `<div class="info-card"><p class="info-label">Lo que te dijo Mira</p><p class="text-sm t-soft">${entry.feedback_mensaje}</p></div>`
          : "";
        openDrawer(entry.emocion_primaria || "Registro", rulerDetailHTML(entry) + fb);
      });
    });
```

- [ ] **Step 4: Estilos del drawer**

Al final de `frontend/styles.css`, añadir:

```css
/* ─── Bottom drawer ─────────────────────────────────────────────────── */
.drawer { position: fixed; inset: 0; z-index: 250; display: none; }
.drawer.open { display: block; }
.drawer-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(74, 67, 56, 0.45);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  animation: modalFade 0.24s ease-out;
}
.drawer-sheet {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  max-height: 84dvh;
  overflow-y: auto;
  background: var(--surface);
  border-radius: 26px 26px 0 0;
  padding: 10px 20px calc(var(--safe-b) + 26px);
  box-shadow: 0 -16px 50px rgba(120, 100, 70, 0.20);
  animation: drawerUp 0.36s var(--ease-soft) both;
  touch-action: none;
}
@keyframes drawerUp {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}
.drawer-handle {
  display: block;
  width: 44px; height: 5px;
  margin: 0 auto 14px;
  border: none;
  border-radius: 999px;
  background: var(--border);
  cursor: pointer;
}
.drawer-sheet h3 {
  margin: 0 0 14px;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text);
  text-transform: capitalize;
}
#drawer-content { display: flex; flex-direction: column; gap: 12px; }
```

- [ ] **Step 5: Verificar sintaxis y navegador**

Run: `node --check frontend/app.js`
Expected: Sin salida.

Verificación en navegador: ir a Historial (con al menos un registro), tocar una tarjeta → el drawer sube desde abajo con el detalle RULER. Cerrarlo con (a) el backdrop, (b) la tecla Escape, (c) arrastrando la hoja hacia abajo.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat(frontend): bottom drawer reutilizable e historial clicable"
```

---

## Task 11: Pantalla de resultados

Muestra el feedback de la IA como protagonista, un campo editable para corregir el texto, el botón "Ver detalles" y el control "¿Te ayudó?".

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`

- [ ] **Step 1: Reescribir `#screen-confirm` en `index.html`**

Reemplazar todo el bloque `<div id="screen-confirm" ...>...</div>` por:

```html
  <!-- ─── Confirmar ──────────────────────────────────────────────────────── -->
  <div id="screen-confirm" class="screen">
    <div class="confirm-body">
      <div class="confirm-header">
        <div class="mira mira-confirm" aria-hidden="true">
          <div class="mira-anim"><div class="mira-tilt"><div class="mira-face">
            <img class="mira-body" src="/assets/mira.png" alt=""
              onerror="this.onerror=null;this.classList.add('img-missing');this.src='data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'" />          </div></div></div>
        </div>
        <h2 data-screen-title>Esto es lo que entendí</h2>
      </div>

      <div id="feedback-card" class="feedback-card"></div>

      <div id="feedback-rating" class="feedback-rating">
        <span class="feedback-rating-q">¿Te ayudó este mensaje?</span>
        <div class="feedback-rating-btns">
          <button id="rate-yes" class="rate-btn" type="button" aria-label="Sí, me ayudó">
            <i data-lucide="thumbs-up" aria-hidden="true"></i>
          </button>
          <button id="rate-no" class="rate-btn" type="button" aria-label="No me ayudó">
            <i data-lucide="thumbs-down" aria-hidden="true"></i>
          </button>
        </div>
      </div>

      <label for="confirm-text" class="confirm-text-label">Lo que entendí que dijiste</label>
      <textarea id="confirm-text" rows="3"></textarea>
      <button id="btn-reanalyze" class="btn-ghost hidden" type="button">Actualizar análisis</button>

      <button id="btn-details" class="btn-details" type="button">
        <i data-lucide="sliders-horizontal" aria-hidden="true"></i><span>Ver detalles</span>
      </button>
    </div>
    <div class="confirm-actions">
      <button id="btn-confirm-save" class="btn-primary" type="button">Guardar</button>
      <button id="btn-confirm-cancel" class="btn-ghost" type="button">Cancelar</button>
    </div>
  </div>
```

- [ ] **Step 2: Añadir `feedbackReaction` al estado**

En `frontend/app.js`, en el objeto `state`, añadir la propiedad:

```javascript
  feedbackReaction: null,
```

- [ ] **Step 3: Reemplazar `onAnalysisReady` y `renderRulerDisplay`/`renderAcompanamiento`**

En `frontend/app.js`, reemplazar la función `onAnalysisReady` completa, y eliminar las funciones `renderRulerDisplay`, `renderAcompanamiento` y `loadHomeCompanion` (ya no se usan), por:

```javascript
function onAnalysisReady(data) {
  state.rulerResult = data;
  stopAnalyzingCopy();
  if (data.crisis_flag) showCrisisModal();
  renderFeedbackCard(data.feedback);
  setFeedbackReaction(null);
  const ta = document.getElementById("confirm-text");
  ta.value = data.transcripcion || "";
  ta.dataset.original = ta.value;
  document.getElementById("btn-reanalyze").classList.add("hidden");
  showScreen("confirm");
}

// Render seguro (textContent): el mensaje viene del LLM, nunca como HTML.
function renderFeedbackCard(feedback) {
  const el = document.getElementById("feedback-card");
  el.innerHTML = "";
  el.className = "feedback-card" + (feedback?.modo ? ` modo-${feedback.modo}` : "");
  const img = document.createElement("img");
  img.src = "/assets/mira.png";
  img.alt = "";
  img.className = "feedback-mira";
  img.onerror = () => img.classList.add("img-missing");
  const p = document.createElement("p");
  p.textContent = feedback?.mensaje || "Gracias por registrar cómo te sientes.";
  el.append(img, p);
}

function setFeedbackReaction(value) {
  state.feedbackReaction = value;
  document.getElementById("rate-yes").classList.toggle("active", value === "me_ayudo");
  document.getElementById("rate-no").classList.toggle("active", value === "no_me_ayudo");
}
```

- [ ] **Step 4: Cablear los controles nuevos**

En `frontend/app.js`, en el bloque `CONFIRM`, después de la declaración de `btnConfirmSave`, reemplazar las constantes `confirmActions`/`btnConfirmDone` y los handlers afectados. Reemplazar el bloque que va desde `const confirmActions = ...` hasta el final del handler `btnConfirmDone.addEventListener(...)` por:

```javascript
document.getElementById("rate-yes").addEventListener("click", () =>
  setFeedbackReaction(state.feedbackReaction === "me_ayudo" ? null : "me_ayudo"));
document.getElementById("rate-no").addEventListener("click", () =>
  setFeedbackReaction(state.feedbackReaction === "no_me_ayudo" ? null : "no_me_ayudo"));

// El campo editable: si se corrige el texto, aparece "Actualizar análisis".
const confirmText = document.getElementById("confirm-text");
confirmText.addEventListener("input", () => {
  const changed = confirmText.value.trim() !== (confirmText.dataset.original || "").trim();
  document.getElementById("btn-reanalyze").classList.toggle("hidden", !changed);
});
document.getElementById("btn-reanalyze").addEventListener("click", () => {
  const txt = confirmText.value.trim();
  if (txt.length >= 3) analyzeText(txt);
});

document.getElementById("btn-details").addEventListener("click", () => {
  if (state.rulerResult) openDrawer("Detalles del registro", rulerDetailHTML(state.rulerResult));
});

btnConfirmSave.addEventListener("click", async () => {
  if (!state.rulerResult) return;
  btnConfirmSave.disabled = true;
  btnConfirmSave.textContent = "Guardando…";
  try {
    const payload = { ...state.rulerResult, reaccion_feedback: state.feedbackReaction };
    const res = await fetch(`${API}/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    resetRecordState();
    showScreen("mood");
  } catch (err) {
    console.error(err);
    btnConfirmSave.textContent = "Reintentar guardar";
  } finally {
    btnConfirmSave.disabled = false;
  }
});

document.getElementById("btn-confirm-cancel").addEventListener("click", () => {
  resetRecordState();
  showScreen("mood");
});
```

- [ ] **Step 5: Actualizar `resetRecordState`**

En `frontend/app.js`, reemplazar la función `resetRecordState` completa por:

```javascript
function resetRecordState() {
  state.audioBlob = null;
  state.pendingText = null;
  state.rulerResult = null;
  state.feedbackReaction = null;
  recState = "idle";
  recMode = null;
  stopWhenReady = false;
  recordBtn.classList.remove("recording", "toggle");
  recordStatus.textContent = "Toca o mantén presionado para hablar";
  setInputMode("voz");
  document.getElementById("text-input").value = "";
  stopRecordTimer();
  btnCancelRecord.classList.add("hidden");
  btnConfirmSave.disabled = false;
  btnConfirmSave.textContent = "Guardar";
  const ta = document.getElementById("confirm-text");
  ta.value = "";
  ta.dataset.original = "";
  document.getElementById("btn-reanalyze").classList.add("hidden");
}
```

- [ ] **Step 6: Estilos de la pantalla de resultados**

En `frontend/styles.css`, reemplazar el bloque "Acompañamiento de Mira" completo (desde `#companion-card { ... }` hasta el cierre de `.companion-close:active`, incluyendo `.companion-home`) por:

```css
/* ─── Tarjeta de feedback de Mira ───────────────────────────────────── */

.feedback-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
  border: 1px solid var(--border);
  margin-bottom: 12px;
  animation: cardIn 0.45s var(--ease-soft) both;
}
.feedback-card.modo-apoyo {
  border-color: color-mix(in srgb, var(--indigo) 32%, transparent);
}
.feedback-mira {
  width: 46px; height: 46px;
  flex-shrink: 0;
  object-fit: contain;
  filter: drop-shadow(0 3px 9px rgba(125, 114, 214, 0.35));
}
.feedback-mira.img-missing {
  border-radius: 50%;
  font-size: 0;
  background: radial-gradient(circle at 38% 30%, #7D72D6, #5B53C9 60%, #3F3895);
}
.feedback-card p {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.55;
  color: var(--text);
}

.feedback-rating {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 18px;
  padding: 0 4px;
}
.feedback-rating-q { font-size: 0.82rem; color: var(--text-dim); }
.feedback-rating-btns { display: flex; gap: 8px; }
.rate-btn {
  width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text-dim);
  cursor: pointer;
  transition: transform 0.16s var(--ease-spring), background 0.18s ease, color 0.18s ease;
}
.rate-btn svg { width: 18px; height: 18px; }
.rate-btn:active { transform: scale(0.92); }
.rate-btn.active {
  background: linear-gradient(135deg, var(--indigo-light), var(--indigo));
  border-color: transparent;
  color: #fff;
}

.confirm-text-label {
  display: block;
  font-size: 0.7rem;
  color: var(--text-dim);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
#confirm-text {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px 14px;
  font: inherit;
  font-size: 1rem;
  color: var(--text);
  resize: none;
  outline: none;
  transition: border-color 0.18s ease;
}
#confirm-text:focus { border-color: var(--indigo); }
#btn-reanalyze { margin-top: 10px; }

.btn-details {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 14px 0 0;
  padding: 8px 4px;
  border: none;
  background: none;
  color: var(--indigo);
  font: inherit;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-details svg { width: 16px; height: 16px; }
```

> Nota: NO incluir aquí `.insight-line` — esa regla está más abajo en el archivo, fuera del rango a reemplazar, y la sigue usando la pantalla de Patrones. El rango a reemplazar va exactamente de `#companion-card` a `.companion-close:active`.

- [ ] **Step 7: Verificar sintaxis y navegador**

Run: `node --check frontend/app.js`
Expected: Sin salida.

Verificación en navegador (backend corriendo): registrar una emoción con voz y con texto. En Resultados confirmar que (a) el feedback de Mira se muestra arriba; (b) "¿Te ayudó?" marca/desmarca; (c) editar el texto muestra "Actualizar análisis" y al pulsarlo se re-analiza; (d) "Ver detalles" abre el drawer con el RULER; (e) Guardar vuelve al Mood Meter; (f) Cancelar descarta.

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css
git commit -m "feat(frontend): pantalla de resultados con feedback, texto editable y reacción"
```

---

## Task 12: Modo noche (`prefers-color-scheme`)

Variante oscura cálida que se activa con la preferencia del sistema, sobreescribiendo las variables CSS.

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/styles.css`

- [ ] **Step 1: `theme-color` para modo noche**

En `frontend/index.html`, reemplazar la línea:

```html
  <meta name="theme-color" content="#F7F1E6" />
```

por:

```html
  <meta name="theme-color" content="#F7F1E6" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#1A1714" media="(prefers-color-scheme: dark)" />
```

- [ ] **Step 2: Hacer adaptables los gradientes de cuadrante**

En `frontend/styles.css`, en las cuatro reglas `.quadrant-red`, `.quadrant-yellow`, `.quadrant-blue`, `.quadrant-green`, reemplazar `#FFFFFF` por `var(--quad-hi)` en cada `linear-gradient`. Y en `:root`, añadir tras la línea `--surface-2: #F1E9D8;`:

```css
  --quad-hi: #FFFFFF;
```

- [ ] **Step 3: Añadir el bloque de modo noche**

Al final de `frontend/styles.css`, añadir:

```css
/* ─── Modo noche (sigue la preferencia del sistema) ─────────────────── */
@media (prefers-color-scheme: dark) {
  :root {
    --red: #E08A6E;        --red-soft: #3A2A24;
    --yellow: #D9B25C;     --yellow-soft: #3A3324;
    --blue: #8FAAC4;       --blue-soft: #26303A;
    --green: #8FB592;      --green-soft: #26332A;
    --indigo: #8C84E6;
    --indigo-light: #A49CEC;
    --bg: #1A1714;
    --surface: #23201B;
    --surface-2: #2E2A23;
    --border: rgba(220, 200, 170, 0.12);
    --text: #EDE6D8;
    --text-dim: #A89E8E;
    --quad-hi: #2E2A23;
  }
  body {
    background-image:
      radial-gradient(circle at 50% -15%, rgba(140, 132, 230, 0.12) 0%, transparent 60%),
      radial-gradient(circle at 100% 110%, rgba(224, 138, 110, 0.08) 0%, transparent 45%);
  }
  /* La superposición glossy de los cuadrantes sería un brillo raro en oscuro */
  .quadrant::before { opacity: 0.06; }
  .t-soft { color: #C3BBA9; }
  #tab-bar { background: rgba(35, 32, 27, 0.88); }
  .skel-line {
    background: linear-gradient(90deg, var(--surface-2) 25%, #3A352B 50%, var(--surface-2) 75%);
    background-size: 200% 100%;
  }
}
```

- [ ] **Step 4: Verificar en navegador**

Verificación en navegador: en DevTools → Rendering → "Emulate CSS media feature prefers-color-scheme", alternar entre `light` y `dark`. En `dark`, recorrer todas las pantallas (Mood Meter, sub-matriz, grabar, análisis, resultados, historial, patrones, chat, drawer, modal de crisis) y confirmar que el texto se lee bien (contraste AA) y no quedan zonas blancas crudas. Verificar también `light`.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/styles.css
git commit -m "feat(frontend): modo noche con prefers-color-scheme"
```

---

## Verificación final

Tras completar las 12 tareas:

- [ ] Backend: `cd backend && .venv/bin/python -m pytest -q` → toda la suite verde.
- [ ] Frontend: `node --check frontend/app.js` → sin errores.
- [ ] Recorrido completo en navegador (backend + Ollama corriendo): registrar una emoción negativa intensa (debe dar feedback de modo "apoyo") y una positiva (modo "ligero"); verificar que la intensidad varía entre registros distintos; probar Guardar y Cancelar; abrir el detalle desde Historial; alternar modo noche.
- [ ] `git grep -n "reasoning_pipeline\|/api/companion\|loadHomeCompanion\|QUADRANTS = {"` → sin resultados (limpieza completa).
