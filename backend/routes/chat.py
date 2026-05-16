from fastapi import APIRouter
from pydantic import BaseModel
from services.memory_service import search_similar
from services.llm_service import chat_with_context

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/chat")
async def chat(req: ChatRequest):
    sources = search_similar(req.question, top_k=5)
    answer = chat_with_context(req.question, sources)
    return {"answer": answer, "sources": sources}
