import httpx, json, os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b-instruct")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))


def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _strip_reasoning(text: str) -> str:
    """Red de seguridad: si se configura un modelo de razonamiento, su bloque
    cierra con </think>; nos quedamos con lo que viene después. El modelo por
    defecto (qwen3:4b-instruct) no razona, así que suele ser un no-op."""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()


def _ollama_generate(system: str, user: str, json_mode: bool = False) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    if json_mode:
        # Restringe la salida a JSON válido (útil para extract_ruler).
        payload["format"] = "json"
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat", json=payload, timeout=LLM_TIMEOUT
    )
    resp.raise_for_status()
    return _strip_reasoning(resp.json()["message"]["content"])


def extract_ruler(text: str) -> dict:
    system = _load_prompt("ruler_extraction.txt")
    raw = _ollama_generate(system, text, json_mode=True)
    # find JSON block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return json.loads(raw[start:end])


def chat_with_context(question: str, sources: list) -> str:
    system = _load_prompt("chat_system.txt")
    context_block = "\n\n".join(
        f"[{i+1}] {s.get('resumen', '')} ({s.get('emocion_primaria', '')})"
        for i, s in enumerate(sources)
    )
    user = f"Contexto de entradas pasadas:\n{context_block}\n\nPregunta: {question}"
    return _ollama_generate(system, user)
