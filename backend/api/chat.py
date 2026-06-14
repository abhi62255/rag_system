import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_rag_agent
from pipelines.retrieval.graph import RAGAgent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SourceItem(BaseModel):
    filename: str
    chunk_index: int
    doc_type: str
    version: int
    similarity: float
    source: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: RAGAgent = Depends(get_rag_agent),
):
    try:
        answer, sources = agent.answer_question(
            user_message=request.message,
            session_id=request.session_id,
        )
        return ChatResponse(
            answer=answer,
            sources=[SourceItem(**s) for s in sources],
            session_id=request.session_id,
        )
    except Exception as e:
        logger.error(f"Chat error for session {request.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
