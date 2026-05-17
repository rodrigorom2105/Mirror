"""Reconstruye el perfil consolidado recorriendo ChromaDB.

El perfil (SQLite) es un derivado de las entradas (ChromaDB). Si se corrompe
o se borra, este script lo regenera entrada por entrada en orden cronológico.
Conviene correr antes `scripts/backfill_ts.py` para que el orden sea exacto.

    cd backend && python scripts/rebuild_profile.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.db import get_conn, init_db  # noqa: E402
from services.memory_service import _entry_ts, query_entries  # noqa: E402
from services.profile_service import (  # noqa: E402
    regenerate_narrative,
    update_profile_with_entry,
)


def main() -> None:
    init_db()
    conn = get_conn()
    try:
        conn.execute("DELETE FROM profile")
        conn.commit()
    finally:
        conn.close()

    entries = query_entries(limit=1_000_000)
    entries.sort(key=_entry_ts)  # cronológico ascendente: la racha lo exige
    for e in entries:
        update_profile_with_entry(e)
    regenerate_narrative()
    print(f"rebuild_profile: perfil reconstruido desde {len(entries)} entradas.")


if __name__ == "__main__":
    main()
