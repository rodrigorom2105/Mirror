import httpx, json, os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")

def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", name)
    with open(path, encoding="utf-8") as f:
        return f.read()

def _ollama_generate(system: str, user: str) -> str:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]

def extract_ruler(text: str) -> dict:
    system = _load_prompt("ruler_extraction.txt")
    raw = _ollama_generate(system, text)
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
