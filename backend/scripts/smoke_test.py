"""Smoke test end-to-end de la API de Mirror.

Verifica los 7 endpoints del contrato (camino feliz + casos de error) contra
un servidor en marcha. Requiere:
  - el servidor corriendo:  .venv/bin/python -m uvicorn main:app
  - Ollama activo con los modelos qwen3:4b-instruct y qwen3-embedding:0.6b
  - macOS (usa `say` para generar audio de prueba)

Uso:  cd backend && .venv/bin/python scripts/smoke_test.py

El test crea entradas reales (vía /api/save y /api/entry). Para volver al
estado limpio de demo: borra data/chroma_db y corre  python seed_data.py
"""
import os
import subprocess
import sys
import tempfile
import time
import wave

import httpx

BASE = os.getenv("SMOKE_BASE", "http://127.0.0.1:8000")

# Los 10 campos que el prompt RULER exige (crisis_flag lo añade la ruta aparte).
RULER_FIELDS = {
    "emocion_primaria", "emociones_secundarias", "cuadrante", "valencia",
    "energia", "intensidad", "disparador", "contexto", "pensamientos", "resumen",
}

_results = []


def check(name, passed, detail=""):
    _results.append((name, bool(passed)))
    mark = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {mark}  {name}" + (f"   ·   {detail}" if detail else ""))


def section(title):
    print(f"\n── {title}")


def make_speech_audio(text):
    """Genera un clip de voz real con el comando `say` de macOS."""
    path = tempfile.mktemp(suffix=".aiff")
    subprocess.run(["say", "-o", path, text], check=True)
    with open(path, "rb") as f:
        return f.read()


def make_tiny_wav():
    """WAV de 0.3 s (< AUDIO_MIN_DURATION) para probar el rechazo por corto."""
    path = tempfile.mktemp(suffix=".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 4800)  # 0.3 s de silencio
    with open(path, "rb") as f:
        return f.read()


def test_root(client):
    section("GET / — frontend estático")
    r = client.get("/")
    check("GET / → 200", r.status_code == 200, f"HTTP {r.status_code}")
    body = r.text.lower()
    check("sirve HTML", "<html" in body or "<!doctype" in body)


def test_transcribe(client, speech, tiny):
    section("POST /api/transcribe")
    t = time.perf_counter()
    r = client.post("/api/transcribe", files={"audio": ("v.aiff", speech, "audio/aiff")})
    dt = time.perf_counter() - t
    ok = r.status_code == 200
    d = r.json() if ok else {}
    check("audio válido → 200", ok, f"HTTP {r.status_code} en {dt:.1f}s")
    check("trae 'text' no vacío", bool((d.get("text") or "").strip()),
          repr((d.get("text") or "")[:55]))
    check("trae 'duration' numérico", isinstance(d.get("duration"), (int, float)),
          str(d.get("duration")))
    check("Content-Type JSON", "application/json" in r.headers.get("content-type", ""),
          r.headers.get("content-type", ""))
    r = client.post("/api/transcribe")
    check("sin archivo → 422", r.status_code == 422, f"HTTP {r.status_code}")
    r = client.post("/api/transcribe", files={"audio": ("x.txt", b"hola", "text/plain")})
    check("tipo no-audio → 400", r.status_code == 400, f"HTTP {r.status_code}")
    r = client.post("/api/transcribe", files={"audio": ("e.wav", b"", "audio/wav")})
    check("archivo vacío → 422", r.status_code == 422, f"HTTP {r.status_code}")
    r = client.post("/api/transcribe", files={"audio": ("t.wav", tiny, "audio/wav")})
    check("audio < 0.5 s → 422", r.status_code == 422, f"HTTP {r.status_code}")


def test_analyze(client):
    section("POST /api/analyze")
    t = time.perf_counter()
    r = client.post("/api/analyze", json={
        "text": "Hoy me sentí muy ansioso por un examen difícil que tengo mañana."})
    dt = time.perf_counter() - t
    ok = r.status_code == 200
    d = r.json() if ok else {}
    check("texto válido → 200", ok, f"HTTP {r.status_code} en {dt:.1f}s")
    missing = RULER_FIELDS - set(d)
    check("RULER con los 10 campos", not missing, "10/10" if not missing else f"faltan {missing}")
    check("trae crisis_flag", "crisis_flag" in d)
    check("cuadrante válido", d.get("cuadrante") in {"rojo", "amarillo", "azul", "verde"},
          str(d.get("cuadrante")))
    v, e, i = d.get("valencia"), d.get("energia"), d.get("intensidad")
    check("valencia en [-1,1]", isinstance(v, (int, float)) and -1 <= v <= 1, str(v))
    check("energia en [0,1]", isinstance(e, (int, float)) and 0 <= e <= 1, str(e))
    check("intensidad en [1,10]", isinstance(i, (int, float)) and 1 <= i <= 10, str(i))
    check("contexto es objeto", isinstance(d.get("contexto"), dict))
    check("emociones_secundarias es lista", isinstance(d.get("emociones_secundarias"), list))
    r = client.post("/api/analyze", json={})
    check("sin 'text' → 422", r.status_code == 422, f"HTTP {r.status_code}")
    r = client.post("/api/analyze", json={"text": "Ya no quiero vivir, no vale la pena seguir."})
    check("texto de crisis → crisis_flag=true", r.json().get("crisis_flag") is True)
    r = client.post("/api/analyze", json={"text": "Pasé una tarde tranquila leyendo en el parque."})
    check("texto normal → crisis_flag=false", r.json().get("crisis_flag") is False)


def test_save(client):
    section("POST /api/save")
    ruler = {
        "emocion_primaria": "sereno", "emociones_secundarias": ["tranquilo"],
        "cuadrante": "verde", "valencia": 0.6, "energia": 0.3, "intensidad": 4,
        "disparador": "prueba del smoke test",
        "contexto": {"personas": [], "lugar": "casa", "actividad": "test"},
        "pensamientos": ["ok"], "resumen": "Entrada de prueba del smoke test",
        "crisis_flag": False,
    }
    r = client.post("/api/save", json=ruler)
    ok = r.status_code == 200
    d = r.json() if ok else {}
    check("RULER válido → 200", ok, f"HTTP {r.status_code}")
    check("respuesta trae 'id'", bool(d.get("id")))
    check("respuesta trae 'saved_at' (contrato)", "saved_at" in d, str(d.get("saved_at")))
    r = client.post("/api/save", json=["esto no es un dict"])
    check("body no-dict → 422", r.status_code == 422, f"HTTP {r.status_code}")


def test_history(client, initial_total):
    section("GET /api/history")
    r = client.get("/api/history", params={"limit": 100})
    d = r.json()
    check("→ 200 con {entries,total}", r.status_code == 200 and "entries" in d and "total" in d)
    check("total refleja la entrada de /save", d["total"] == initial_total + 1,
          f"{d['total']} (esperado {initial_total + 1})")
    r = client.get("/api/history", params={"limit": 3})
    check("limit=3 devuelve 3", len(r.json()["entries"]) == 3)
    entries = client.get("/api/history", params={"limit": 100}).json()["entries"]
    dates = [e.get("saved_at", "") for e in entries]
    check("orden por saved_at descendente", dates == sorted(dates, reverse=True))
    check("entradas conservan 'contexto' anidado",
          any(isinstance(e.get("contexto"), dict) for e in entries))
    r = client.get("/api/history", params={"limit": 0})
    check("limit=0 → 422", r.status_code == 422, f"HTTP {r.status_code}")
    r = client.get("/api/history", params={"limit": 200})
    check("limit=200 → 422", r.status_code == 422, f"HTTP {r.status_code}")


def test_patterns(client):
    section("GET /api/patterns")
    r = client.get("/api/patterns")
    d = r.json()
    check("→ 200", r.status_code == 200, f"HTTP {r.status_code}")
    check("trae mini_mood_meter", isinstance(d.get("mini_mood_meter"), dict))
    check("trae palabras_frecuentes", isinstance(d.get("palabras_frecuentes"), list))
    check("trae patron_detectado", bool(d.get("patron_detectado")))
    total = client.get("/api/history", params={"limit": 100}).json()["total"]
    s = sum(d.get("mini_mood_meter", {}).values())
    check("mini_mood_meter suma = total entradas", s == total, f"{s} vs {total}")


def test_chat(client):
    section("POST /api/chat")
    t = time.perf_counter()
    r = client.post("/api/chat", json={"question": "¿Cómo he estado emocionalmente?"})
    dt = time.perf_counter() - t
    ok = r.status_code == 200
    d = r.json() if ok else {}
    check("pregunta válida → 200", ok, f"HTTP {r.status_code} en {dt:.1f}s")
    check("trae 'answer' no vacío", bool((d.get("answer") or "").strip()))
    check("answer sin fuga de razonamiento", "</think>" not in (d.get("answer") or ""))
    check("trae 'sources' (lista)", isinstance(d.get("sources"), list))
    check("usa contexto (sources > 0)", len(d.get("sources", [])) > 0,
          f"{len(d.get('sources', []))} fuentes")
    r = client.post("/api/chat", json={})
    check("sin 'question' → 422", r.status_code == 422, f"HTTP {r.status_code}")


def test_entry(client, speech):
    section("POST /api/entry — orquestación transcribe+analyze+save")
    before = client.get("/api/history", params={"limit": 100}).json()["total"]
    t = time.perf_counter()
    r = client.post("/api/entry",
                    files={"audio": ("v.aiff", speech, "audio/aiff")},
                    data={"emocion_seleccionada": "ansioso"})
    dt = time.perf_counter() - t
    ok = r.status_code == 200
    d = r.json() if ok else {}
    check("audio + emoción → 200", ok, f"HTTP {r.status_code} en {dt:.1f}s")
    check("devuelve 'id'", bool(d.get("id")))
    check("devuelve 'transcripcion'", bool((d.get("transcripcion") or "").strip()),
          repr((d.get("transcripcion") or "")[:55]))
    check("conserva 'emocion_seleccionada'", d.get("emocion_seleccionada") == "ansioso")
    missing = RULER_FIELDS - set(d)
    check("incluye estructura RULER", not missing, "10/10" if not missing else f"faltan {missing}")
    check("incluye crisis_flag", "crisis_flag" in d)
    after = client.get("/api/history", params={"limit": 100}).json()["total"]
    check("la entrada se persistió", after == before + 1, f"{after} (esperado {before + 1})")
    r = client.post("/api/entry", files={"audio": ("v.aiff", speech, "audio/aiff")})
    check("sin emocion_seleccionada → 422", r.status_code == 422, f"HTTP {r.status_code}")
    r = client.post("/api/entry", data={"emocion_seleccionada": "feliz"})
    check("sin audio → 422", r.status_code == 422, f"HTTP {r.status_code}")


def test_encoding(client):
    section("Codificación UTF-8")
    entries = client.get("/api/history", params={"limit": 100}).json()["entries"]
    blob = " ".join(e.get("resumen", "") for e in entries)
    check("acentos UTF-8 intactos en respuestas", any(c in blob for c in "áéíóúñ"))


def main():
    print(f"Smoke test de Mirror → {BASE}")
    try:
        httpx.get(BASE + "/", timeout=5)
    except httpx.HTTPError:
        print(f"\nERROR: el servidor no responde en {BASE}")
        print("Arráncalo:  cd backend && .venv/bin/python -m uvicorn main:app")
        sys.exit(2)

    client = httpx.Client(base_url=BASE, timeout=300)
    started = time.perf_counter()

    initial_total = client.get("/api/history", params={"limit": 100}).json()["total"]
    print(f"Estado inicial: {initial_total} entradas en la base.")
    speech = make_speech_audio("Hola, esta es una prueba de transcripción de voz.")
    tiny = make_tiny_wav()

    stages = [
        ("root", lambda: test_root(client)),
        ("transcribe", lambda: test_transcribe(client, speech, tiny)),
        ("analyze", lambda: test_analyze(client)),
        ("save", lambda: test_save(client)),
        ("history", lambda: test_history(client, initial_total)),
        ("patterns", lambda: test_patterns(client)),
        ("chat", lambda: test_chat(client)),
        ("entry", lambda: test_entry(client, speech)),
        ("encoding", lambda: test_encoding(client)),
    ]
    for name, fn in stages:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - reportar, no abortar
            check(f"[{name}] ejecución sin excepción", False,
                  f"{type(exc).__name__}: {exc}")

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    elapsed = time.perf_counter() - started
    print(f"\n{'=' * 56}")
    print(f"  RESULTADO: {passed}/{total} verificaciones — {elapsed:.0f}s")
    if passed != total:
        print("  FALLARON:")
        for name, ok in _results:
            if not ok:
                print(f"    ✗ {name}")
        print("=" * 56)
        sys.exit(1)
    print("  ✓ API AL 100%")
    print("=" * 56)


if __name__ == "__main__":
    main()
