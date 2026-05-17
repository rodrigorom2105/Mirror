import chromadb, uuid, json, os, time
from datetime import datetime
from chromadb.config import Settings
from services.embedding_service import embed

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma_db")
_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False),
)
_collection = _client.get_or_create_collection("mirror_entries")

# Pesos del scoring de recuperación — tunables vía .env sin tocar código.
_W_SIM = float(os.getenv("RETRIEVE_W_SIM", "0.6"))
_W_RECENCY = float(os.getenv("RETRIEVE_W_RECENCY", "0.3"))
_W_INTENSITY = float(os.getenv("RETRIEVE_W_INTENSITY", "0.1"))
_HALF_LIFE_DAYS = float(os.getenv("RETRIEVE_HALF_LIFE_DAYS", "14"))

# Agrupación de cuadrantes RULER por valencia.
CUADRANTES_NEGATIVOS = {"rojo", "azul"}
CUADRANTES_POSITIVOS = {"verde", "amarillo"}


def _to_metadata(ruler: dict) -> dict:
    """Aplana el RULER a metadata de Chroma.

    Chroma solo admite escalares como metadata; los campos compuestos
    (emociones_secundarias, pensamientos, contexto) se serializan a JSON
    para no perderlos al guardar.
    """
    meta = {}
    for key, value in ruler.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            meta[key] = value
        else:
            meta[key] = json.dumps(value, ensure_ascii=False)
    return meta


def _from_metadata(meta: dict) -> dict:
    """Reconstruye el RULER deserializando los campos guardados como JSON."""
    entry = {}
    for key, value in meta.items():
        if isinstance(value, str) and value[:1] in ("[", "{"):
            try:
                entry[key] = json.loads(value)
            except json.JSONDecodeError:
                entry[key] = value
        else:
            entry[key] = value
    return entry


def _epoch_from_iso(iso: str) -> float:
    """Convierte un timestamp ISO a epoch; 0.0 si es inválido o falta."""
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _entry_ts(entry: dict) -> float:
    """Epoch de una entrada — usa `ts` si existe, si no deriva de `saved_at`."""
    return entry.get("ts") or _epoch_from_iso(entry.get("saved_at", ""))


def save_entry(ruler: dict) -> tuple[str, str]:
    entry_id = str(uuid.uuid4())
    ctx = ruler.get("contexto") if isinstance(ruler.get("contexto"), dict) else {}
    # Embedding más rico: además del resumen, incluye pensamientos y contexto
    # para que la recuperación semántica encuentre por actividad/lugar/idea.
    text_for_embed = " ".join(filter(None, [
        ruler.get("resumen", ""),
        ruler.get("emocion_primaria", ""),
        ruler.get("disparador", ""),
        " ".join(ruler.get("pensamientos") or []),
        ctx.get("actividad", ""),
        ctx.get("lugar", ""),
    ]))
    vector = embed(text_for_embed)
    meta = _to_metadata(ruler)
    # Respeta un saved_at provisto (p. ej. datos sintéticos); si no, ahora.
    meta.setdefault("saved_at", datetime.utcnow().isoformat())
    # `ts` epoch: permite rangos numéricos inequívocos en los filtros de Chroma.
    meta["ts"] = _epoch_from_iso(meta["saved_at"]) or time.time()
    _collection.add(
        ids=[entry_id],
        embeddings=[vector],
        documents=[text_for_embed],
        metadatas=[meta],
    )
    return entry_id, meta["saved_at"]


def _build_where(cuadrante=None, cuadrantes=None, since=None, until=None):
    """Arma un filtro `where` de Chroma a partir de los criterios dados.

    `since`/`until` son epoch (segundos). Devuelve None si no hay filtros.
    """
    clauses = []
    if cuadrante:
        clauses.append({"cuadrante": {"$eq": cuadrante}})
    if cuadrantes:
        clauses.append({"cuadrante": {"$in": list(cuadrantes)}})
    if since is not None:
        clauses.append({"ts": {"$gte": float(since)}})
    if until is not None:
        clauses.append({"ts": {"$lte": float(until)}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def query_entries(cuadrante=None, cuadrantes=None, since=None, until=None,
                   limit: int = 20) -> list:
    """Recupera entradas con filtros opcionales (cuadrante, rango de fechas).

    Usa el `where` nativo de Chroma cuando hay filtros — evita traer toda la
    colección a Python. Ordena por fecha descendente y corta a `limit`.
    """
    where = _build_where(cuadrante, cuadrantes, since, until)
    kwargs = {"include": ["metadatas"]}
    if where:
        kwargs["where"] = where
    result = _collection.get(**kwargs)
    entries = []
    for i, meta in enumerate(result.get("metadatas") or []):
        entry = _from_metadata(meta)
        entry["id"] = result["ids"][i]
        entries.append(entry)
    entries.sort(key=_entry_ts, reverse=True)
    return entries[:limit]


def get_history(limit: int = 20) -> list:
    """Las `limit` entradas más recientes (compat: misma firma que antes)."""
    return query_entries(limit=limit)


def retrieve_relevant(text: str, top_k: int = 5, cuadrante=None,
                      cuadrantes=None, since=None) -> list:
    """Recupera entradas relevantes a `text` con scoring combinado.

    Sobre-trae candidatos por similitud semántica y los re-ordena con
    `score = 0.6·similitud + 0.3·recencia + 0.1·intensidad`. Cada entrada
    devuelta lleva `_score`. Acepta filtros (cuadrante, fecha).
    """
    n = _collection.count()
    if n == 0:
        return []
    where = _build_where(cuadrante, cuadrantes, since, None)
    kwargs = {
        "query_embeddings": [embed(text)],
        "n_results": min(top_k * 4, n),
        "include": ["metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    result = _collection.query(**kwargs)
    metas = result["metadatas"][0] if result.get("metadatas") else []
    dists = result["distances"][0] if result.get("distances") else []
    ids = result["ids"][0] if result.get("ids") else []
    now = time.time()
    scored = []
    for i, meta in enumerate(metas):
        entry = _from_metadata(meta)
        entry["id"] = ids[i] if i < len(ids) else None
        # Chroma usa distancia L2 por defecto; 1/(1+d) la mapea a (0,1] de
        # forma monótona sin asumir un espacio métrico concreto.
        dist = dists[i] if i < len(dists) else 1.0
        sim = 1.0 / (1.0 + max(dist, 0.0))
        ts = _entry_ts(entry)
        age_days = max((now - ts) / 86400.0, 0.0) if ts else 999.0
        recency = 0.5 ** (age_days / _HALF_LIFE_DAYS)
        intensity = (entry.get("intensidad") or 0) / 10.0
        entry["_score"] = _W_SIM * sim + _W_RECENCY * recency + _W_INTENSITY * intensity
        scored.append(entry)
    scored.sort(key=lambda e: e["_score"], reverse=True)
    return scored[:top_k]


def search_similar(text: str, top_k: int = 5) -> list:
    """Compat: búsqueda semántica simple. Delega en retrieve_relevant."""
    return retrieve_relevant(text, top_k=top_k)


def _relative_date(ts: float) -> str:
    """Fecha relativa legible a partir de un epoch."""
    if not ts:
        return "fecha desconocida"
    days = int((time.time() - ts) / 86400)
    if days <= 0:
        return "hoy"
    if days == 1:
        return "ayer"
    if days < 7:
        return f"hace {days} días"
    if days < 30:
        return f"hace {days // 7} semana(s)"
    return f"hace {days // 30} mes(es)"


def format_context_block(entries: list) -> str:
    """Formatea entradas como contexto rico para inyectar al LLM."""
    lines = []
    for i, e in enumerate(entries, 1):
        ctx = e.get("contexto") if isinstance(e.get("contexto"), dict) else {}
        personas = ", ".join(ctx.get("personas", []) or [])
        partes = [
            f"[{i}] ({_relative_date(_entry_ts(e))}) {e.get('resumen', '')}",
            f"emoción: {e.get('emocion_primaria', '?')} "
            f"({e.get('cuadrante', '?')}, intensidad {e.get('intensidad', '?')}/10)",
        ]
        if e.get("disparador"):
            partes.append(f"disparador: {e['disparador']}")
        if ctx.get("actividad"):
            partes.append(f"actividad: {ctx['actividad']}")
        if personas:
            partes.append(f"personas: {personas}")
        lines.append(" — ".join(partes))
    return "\n".join(lines)


def compute_patterns() -> dict:
    entries = get_history(limit=100)
    if not entries:
        return {"mini_mood_meter": {}, "palabras_frecuentes": [], "patron_detectado": "Sin datos aún."}

    cuadrante_counts = {}
    word_freq = {}
    for e in entries:
        c = e.get("cuadrante", "desconocido")
        cuadrante_counts[c] = cuadrante_counts.get(c, 0) + 1
        for word in e.get("emocion_primaria", "").split():
            word_freq[word] = word_freq.get(word, 0) + 1

    top_words = sorted(word_freq, key=word_freq.get, reverse=True)[:5]
    dominant = max(cuadrante_counts, key=cuadrante_counts.get) if cuadrante_counts else "N/A"
    patron = f"Tendencia predominante: cuadrante {dominant} ({cuadrante_counts.get(dominant, 0)} de {len(entries)} registros)"

    return {
        "mini_mood_meter": cuadrante_counts,
        "palabras_frecuentes": top_words,
        "patron_detectado": patron,
    }


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
    except Exception:  # noqa: BLE001 - la reacción es un extra, no crítica
        return False
    metas = existing.get("metadatas") or []
    if not metas or metas[0] is None:
        return False
    meta = dict(metas[0])
    meta["feedback_reaccion"] = reaccion
    try:
        _collection.update(ids=[entry_id], metadatas=[meta])
    except Exception:  # noqa: BLE001 - la reacción es un extra, no crítica
        return False
    return True
