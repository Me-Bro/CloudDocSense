from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    workspace_id: str = "default"
    conversation_id: str | None = None


@router.post("/")
async def query_documents(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    # M1: retrieval + grounded generation + SSE streaming
    return {
        "answer": "RAG pipeline not yet implemented (M1)",
        "citations": [],
        "grounded": False,
        "workspace_id": req.workspace_id,
    }
