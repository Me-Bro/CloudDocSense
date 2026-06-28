import json
import uuid

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import AsyncSessionLocal, get_db
from app.models import Conversation, Message
from app.models.search_history import SearchHistory
from app.models.user import User
from app.services import generation, retrieval
from app.services.auth import decode_user_id, get_current_user

router = APIRouter()
log = structlog.get_logger()

HISTORY_LIMIT = 6


class QueryRequest(BaseModel):
    question: str
    workspace_id: str = "default"
    conversation_id: str | None = None


async def _get_or_create_conversation(
    db: AsyncSession, conversation_id: str | None, workspace_id: str, user_id: str | None
) -> Conversation:
    if conversation_id:
        conv = await db.get(Conversation, conversation_id)
        if conv:
            return conv
    conv = Conversation(id=str(uuid.uuid4()), workspace_id=workspace_id, user_id=user_id)
    db.add(conv)
    await db.flush()
    return conv


async def _history(db: AsyncSession, conversation_id: str) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    msgs = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in msgs]


async def _save_search_history(
    db: AsyncSession, user_id: str, workspace_id: str, question: str, chunks: list[dict]
) -> None:
    doc_ids = list({c["document_id"] for c in chunks})
    db.add(
        SearchHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workspace_id=workspace_id,
            query_text=question,
            result_count=len(chunks),
            doc_ids=doc_ids,
        )
    )


@router.post("/")
async def query_documents(
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    log.info("query.start", workspace_id=req.workspace_id, question=req.question[:80], streaming=False)
    conv = await _get_or_create_conversation(db, req.conversation_id, req.workspace_id, current_user.id)
    history = await _history(db, conv.id)
    log.info("query.context", conversation_id=conv.id, history_msgs=len(history))

    chunks = await retrieval.retrieve(db, req.workspace_id, req.question)

    db.add(Message(conversation_id=conv.id, role="user", content=req.question))
    await _save_search_history(db, current_user.id, req.workspace_id, req.question, chunks)

    if not chunks:
        log.info("query.decision", path="not_found", reason="no_chunks_above_threshold")
        answer, grounded, citations = generation.NOT_FOUND, False, []
    else:
        citations = generation.citations_from(chunks)
        grounded = True
        try:
            log.info("query.generate", chunks=len(chunks))
            answer = generation.generate_answer(req.question, chunks, history)
            if generation.NOT_FOUND in answer:
                grounded, citations = False, []
                log.info("query.decision", path="not_found", reason="llm_ungrounded")
            else:
                log.info("query.decision", path="grounded", answer_chars=len(answer))
        except Exception as e:
            log.warning("query.generation_failed", error=type(e).__name__)
            answer = (
                f"(Generation unavailable: {type(e).__name__}. Set a valid OPENROUTER_API_KEY.)\n\n"
                "Top retrieved context:\n\n"
                + "\n---\n".join(c["text"][:300] for c in chunks)
            )

    db.add(Message(conversation_id=conv.id, role="assistant", content=answer, citations=citations))
    log.info("query.done", conversation_id=conv.id, grounded=grounded, citations=len(citations))

    return {
        "answer": answer,
        "citations": citations,
        "grounded": grounded,
        "workspace_id": req.workspace_id,
        "conversation_id": conv.id,
    }


@router.post("/stream")
async def query_stream(req: QueryRequest, request: Request):
    """SSE token streaming: 'meta' -> 'delta'* -> 'done'.

    Reads Bearer token from Authorization header to associate history with user.
    """
    log.info("query.start", workspace_id=req.workspace_id, question=req.question[:80], streaming=True)

    auth_header = request.headers.get("Authorization", "")
    user_id: str | None = None
    if auth_header.startswith("Bearer "):
        user_id = decode_user_id(auth_header[7:])

    async def gen():
        async with AsyncSessionLocal() as db:
            conv = await _get_or_create_conversation(db, req.conversation_id, req.workspace_id, user_id)
            history = await _history(db, conv.id)
            chunks = await retrieval.retrieve(db, req.workspace_id, req.question)
            db.add(Message(conversation_id=conv.id, role="user", content=req.question))
            if user_id:
                await _save_search_history(db, user_id, req.workspace_id, req.question, chunks)
            await db.commit()

            if not chunks:
                yield {"event": "meta", "data": json.dumps(
                    {"conversation_id": conv.id, "grounded": False, "citations": []})}
                yield {"event": "delta", "data": generation.NOT_FOUND}
                db.add(Message(conversation_id=conv.id, role="assistant", content=generation.NOT_FOUND))
                await db.commit()
                yield {"event": "done", "data": json.dumps({"grounded": False, "citations": []})}
                return

            citations = generation.citations_from(chunks)
            yield {"event": "meta", "data": json.dumps(
                {"conversation_id": conv.id, "grounded": True, "citations": citations})}

            parts: list[str] = []
            try:
                for delta in generation.stream_answer(req.question, chunks, history):
                    parts.append(delta)
                    yield {"event": "delta", "data": delta}
            except Exception as e:
                msg = f"(Generation unavailable: {type(e).__name__}.)"
                parts.append(msg)
                yield {"event": "delta", "data": msg}

            answer = "".join(parts)
            grounded = generation.NOT_FOUND not in answer
            final_citations = citations if grounded else []
            db.add(Message(
                conversation_id=conv.id, role="assistant", content=answer, citations=final_citations))
            await db.commit()
            yield {"event": "done", "data": json.dumps(
                {"grounded": grounded, "citations": final_citations})}

    return EventSourceResponse(gen())
