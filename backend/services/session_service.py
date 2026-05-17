"""Memoria de sesión/conversación del chat (nivel C).

Da continuidad al chat: los mensajes dentro de una conversación y, entre
sesiones, un resumen de la anterior. Vive en SQLite (ver db.py).

Una "sesión" se reutiliza si la última tuvo actividad hace poco (idle corto);
si no, se abre una nueva. Así el frontend no necesita gestionar IDs.
"""
import json
import os
import uuid
from datetime import datetime, timedelta

from services.db import get_conn

_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "30"))


def get_or_create_active_session(idle_minutes: int = _IDLE_MINUTES) -> str:
    """Devuelve la sesión activa, o crea una nueva si la última ya expiró."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, last_active_at FROM sessions "
            "ORDER BY last_active_at DESC LIMIT 1"
        ).fetchone()
        now = datetime.utcnow()
        if row:
            try:
                last = datetime.fromisoformat(row["last_active_at"])
            except (ValueError, TypeError):
                last = now - timedelta(days=1)
            if now - last < timedelta(minutes=idle_minutes):
                return row["id"]
        sid = str(uuid.uuid4())
        iso = now.isoformat()
        conn.execute(
            "INSERT INTO sessions (id, started_at, last_active_at) VALUES (?, ?, ?)",
            (sid, iso, iso),
        )
        conn.commit()
        return sid
    finally:
        conn.close()


def append_message(session_id: str, role: str, content: str,
                   sources: list | None = None) -> None:
    """Guarda un mensaje y actualiza la actividad de la sesión."""
    conn = get_conn()
    try:
        iso = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at, sources) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, iso,
             json.dumps(sources, ensure_ascii=False) if sources else None),
        )
        conn.execute("UPDATE sessions SET last_active_at = ? WHERE id = ?",
                     (iso, session_id))
        conn.commit()
    finally:
        conn.close()


def get_recent_messages(session_id: str, limit: int = 10) -> list:
    """Últimos N mensajes de la sesión, en orden cronológico ascendente."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_last_session_summary(exclude_session_id: str | None = None) -> str | None:
    """Resumen de la conversación anterior — continuidad entre sesiones."""
    conn = get_conn()
    try:
        if exclude_session_id:
            row = conn.execute(
                "SELECT summary FROM sessions WHERE id != ? AND summary IS NOT NULL "
                "ORDER BY last_active_at DESC LIMIT 1", (exclude_session_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT summary FROM sessions WHERE summary IS NOT NULL "
                "ORDER BY last_active_at DESC LIMIT 1"
            ).fetchone()
    finally:
        conn.close()
    return row["summary"] if row else None


def summarize_session(session_id: str) -> None:
    """Resume una sesión con el LLM y guarda el resumen. Best-effort."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < 2:
        return
    try:
        from services.llm_service import _ollama_generate
        convo = "\n".join(f"{r['role']}: {r['content']}" for r in rows)
        system = ("Resume en 1 o 2 frases de qué habló esta conversación sobre "
                  "las emociones del usuario. Español, breve, en tercera persona.")
        resumen = _ollama_generate(system, convo, num_predict=120)
        conn = get_conn()
        try:
            conn.execute("UPDATE sessions SET summary = ? WHERE id = ?",
                         (resumen.strip(), session_id))
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - el resumen es opcional
        pass


def summarize_stale_sessions(except_id: str | None = None, limit: int = 1) -> None:
    """Resume sesiones cerradas que aún no tienen resumen (correr en background)."""
    conn = get_conn()
    try:
        if except_id:
            rows = conn.execute(
                "SELECT id FROM sessions WHERE summary IS NULL AND id != ? "
                "ORDER BY last_active_at DESC LIMIT ?", (except_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id FROM sessions WHERE summary IS NULL "
                "ORDER BY last_active_at DESC LIMIT ?", (limit,)
            ).fetchall()
    finally:
        conn.close()
    for r in rows:
        summarize_session(r["id"])
