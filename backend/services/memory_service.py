import chromadb, uuid, json, os
from datetime import datetime
from services.embedding_service import embed

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma_db")
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection("mirror_entries")

def save_entry(ruler: dict) -> str:
    entry_id = str(uuid.uuid4())
    text_for_embed = f"{ruler.get('resumen', '')} {ruler.get('emocion_primaria', '')} {ruler.get('disparador', '')}"
    vector = embed(text_for_embed)
    meta = {k: v for k, v in ruler.items() if isinstance(v, (str, int, float, bool))}
    meta["saved_at"] = datetime.utcnow().isoformat()
    _collection.add(
        ids=[entry_id],
        embeddings=[vector],
        documents=[text_for_embed],
        metadatas=[meta],
    )
    return entry_id

def get_history(limit: int = 20) -> list:
    result = _collection.get(include=["metadatas", "documents"])
    entries = []
    for i, meta in enumerate(result["metadatas"]):
        entry = dict(meta)
        entry["id"] = result["ids"][i]
        entries.append(entry)
    entries.sort(key=lambda e: e.get("saved_at", ""), reverse=True)
    return entries[:limit]

def search_similar(text: str, top_k: int = 5) -> list:
    vector = embed(text)
    result = _collection.query(
        query_embeddings=[vector],
        n_results=min(top_k, _collection.count()),
        include=["metadatas", "documents"],
    )
    return result["metadatas"][0] if result["metadatas"] else []

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
