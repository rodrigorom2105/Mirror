import chromadb, uuid, json, os
from datetime import datetime
from chromadb.config import Settings
from services.embedding_service import embed

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma_db")
_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False),
)
_collection = _client.get_or_create_collection("mirror_entries")


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


def save_entry(ruler: dict) -> tuple[str, str]:
    entry_id = str(uuid.uuid4())
    text_for_embed = f"{ruler.get('resumen', '')} {ruler.get('emocion_primaria', '')} {ruler.get('disparador', '')}"
    vector = embed(text_for_embed)
    meta = _to_metadata(ruler)
    # Respeta un saved_at provisto (p. ej. datos sintéticos); si no, ahora.
    meta.setdefault("saved_at", datetime.utcnow().isoformat())
    _collection.add(
        ids=[entry_id],
        embeddings=[vector],
        documents=[text_for_embed],
        metadatas=[meta],
    )
    return entry_id, meta["saved_at"]


def get_history(limit: int = 20) -> list:
    result = _collection.get(include=["metadatas", "documents"])
    entries = []
    for i, meta in enumerate(result["metadatas"]):
        entry = _from_metadata(meta)
        entry["id"] = result["ids"][i]
        entries.append(entry)
    entries.sort(key=lambda e: e.get("saved_at", ""), reverse=True)
    return entries[:limit]


def search_similar(text: str, top_k: int = 5) -> list:
    if _collection.count() == 0:
        return []
    vector = embed(text)
    result = _collection.query(
        query_embeddings=[vector],
        n_results=min(top_k, _collection.count()),
        include=["metadatas", "documents"],
    )
    metas = result["metadatas"][0] if result["metadatas"] else []
    return [_from_metadata(m) for m in metas]


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
