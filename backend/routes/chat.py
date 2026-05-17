from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from services.llm_service import chat_with_context
from services.memory_service import retrieve_relevant
from services.profile_service import get_profile_summary_for_prompt
from services.relevance import filter_relevant_sources
from services.session_service import (
    append_message,
    get_last_session_summary,
    get_or_create_active_session,
    get_recent_messages,
    summarize_stale_sessions,
)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None  # opcional; si falta, se resuelve la activa


@router.post("/chat")
async def chat(req: ChatRequest, background: BackgroundTasks):
    # Sesión: continuidad entre mensajes (y entre sesiones cercanas).
    session_id = req.session_id or get_or_create_active_session()
    history = get_recent_messages(session_id, limit=10)

    # Contexto: RAG con scoring + filtrado de lo poco relevante.
    sources = filter_relevant_sources(retrieve_relevant(req.question, top_k=5))

    # Memoria de largo plazo: perfil consolidado + resumen de la sesión anterior.
    profile_summary = get_profile_summary_for_prompt()
    prev = get_last_session_summary(exclude_session_id=session_id)
    if prev:
        profile_summary += f"\n\nResumen de la conversación anterior: {prev}"

    answer = chat_with_context(req.question, sources, history, profile_summary)

    append_message(session_id, "user", req.question)
    append_message(session_id, "assistant", answer,
                   sources=[s.get("id") for s in sources])
    # Resume sesiones viejas sin bloquear la respuesta.
    background.add_task(summarize_stale_sessions, session_id)

    return {"answer": answer, "sources": sources, "session_id": session_id}
