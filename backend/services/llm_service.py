import httpx, json, os, time

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


def _ollama_generate(system: str, user: str, json_mode: bool = False,
                     temperature: float | None = None,
                     num_predict: int | None = None) -> str:
    """Llama a Ollama /api/chat. Un reintento con backoff ante fallo de red.

    `temperature` y `num_predict` (máx. tokens) son opcionales: el
    acompañamiento usa `num_predict` bajo para respuestas cortas y rápidas.
    """
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"  # restringe la salida a JSON válido
    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        payload["options"] = options

    last_exc = None
    for intento in range(2):
        try:
            resp = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=LLM_TIMEOUT)
            resp.raise_for_status()
            return _strip_reasoning(resp.json()["message"]["content"])
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if intento == 0:
                time.sleep(1.5)  # backoff antes del reintento
    raise last_exc


def _ollama_chat(messages: list, temperature: float | None = None,
                 num_predict: int | None = None) -> str:
    """Variante multi-turno: recibe la lista completa de mensajes (system,
    pares user/assistant del historial, y el turno actual)."""
    payload = {"model": LLM_MODEL, "messages": messages, "stream": False}
    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        payload["options"] = options

    last_exc = None
    for intento in range(2):
        try:
            resp = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=LLM_TIMEOUT)
            resp.raise_for_status()
            return _strip_reasoning(resp.json()["message"]["content"])
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if intento == 0:
                time.sleep(1.5)
    raise last_exc


def extract_ruler(text: str) -> dict:
    system = _load_prompt("ruler_extraction.txt")
    raw = _ollama_generate(system, text, json_mode=True)
    # find JSON block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return json.loads(raw[start:end])


def chat_with_context(question: str, sources: list, history: list | None = None,
                      profile_summary: str | None = None) -> str:
    """Responde una pregunta del chat con contexto (RAG + perfil + historial).

    `history` es la lista de mensajes previos de la sesión [{role, content}, ...]
    para dar continuidad a la conversación.
    """
    system = _load_prompt("chat_system.txt")
    if profile_summary:
        system += f"\n\n--- Perfil del usuario (úsalo para personalizar) ---\n{profile_summary}"

    context_block = "\n".join(
        f"[{i + 1}] {s.get('resumen', '')} ({s.get('emocion_primaria', '')})"
        for i, s in enumerate(sources)
    ) or "(sin entradas pasadas relevantes)"
    user = f"Contexto de entradas pasadas:\n{context_block}\n\nPregunta: {question}"

    messages = [{"role": "system", "content": system}]
    for m in (history or []):
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user})
    return _ollama_chat(messages, temperature=0.7)


def generate_companion(evidence_block: str) -> str:
    """Genera el mensaje de acompañamiento a partir de evidencia estructurada.

    Respuesta corta (num_predict bajo) → más rápida con el modelo 4B local.
    """
    system = _load_prompt("companion.txt")
    return _ollama_generate(system, evidence_block, temperature=0.7, num_predict=180)
