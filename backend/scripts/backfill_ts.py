"""Backfill: añade el campo `ts` (epoch) a las entradas que no lo tienen.

Las entradas guardadas antes de la Fase 1 carecen de `ts`. Sin él, los
filtros de rango de fecha de Chroma no pueden acotarlas. Ejecutar una vez:

    cd backend && python scripts/backfill_ts.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.memory_service import _collection, _epoch_from_iso  # noqa: E402


def main() -> None:
    result = _collection.get(include=["metadatas"])
    ids = result["ids"]
    metas = result.get("metadatas") or []
    upd_ids, upd_metas = [], []
    for i, meta in enumerate(metas):
        if meta.get("ts"):
            continue
        meta = dict(meta)
        meta["ts"] = _epoch_from_iso(meta.get("saved_at", ""))
        upd_ids.append(ids[i])
        upd_metas.append(meta)
    if upd_ids:
        _collection.update(ids=upd_ids, metadatas=upd_metas)
    print(f"backfill_ts: {len(upd_ids)} de {len(ids)} entradas actualizadas.")


if __name__ == "__main__":
    main()
