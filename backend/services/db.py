"""Capa de persistencia SQLite para la memoria consolidada y de sesión.

ChromaDB guarda la memoria cruda (las entradas RULER). SQLite guarda los
derivados reconstruibles: el perfil emocional consolidado del usuario y el
historial de conversación del chat. Un solo archivo, modo WAL para soportar
lecturas concurrentes con escrituras atómicas (p. ej. /api/entry y /api/chat
ocurriendo casi a la vez).
"""
import os
import sqlite3

_DB_PATH = os.getenv("PROFILE_DB_PATH", "./data/profile.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
  id          INTEGER PRIMARY KEY CHECK (id = 1),
  data        TEXT NOT NULL,            -- JSON del perfil consolidado
  entry_count INTEGER NOT NULL DEFAULT 0,
  updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id             TEXT PRIMARY KEY,      -- uuid
  started_at     TEXT NOT NULL,
  last_active_at TEXT NOT NULL,
  summary        TEXT                   -- resumen LLM de la sesión (al cerrarse)
);

CREATE TABLE IF NOT EXISTS messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  role       TEXT NOT NULL,             -- 'user' | 'assistant'
  content    TEXT NOT NULL,
  created_at TEXT NOT NULL,
  sources    TEXT                       -- JSON: ids de entradas RULER citadas
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
"""


def get_conn() -> sqlite3.Connection:
    """Conexión SQLite con WAL y filas accesibles por nombre de columna."""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Crea las tablas si no existen. Idempotente — seguro en cada arranque."""
    os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
    conn = get_conn()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
