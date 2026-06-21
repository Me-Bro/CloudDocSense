import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import AsyncSessionLocal, get_db
from app.models import Conversation, Message
from app.services import generation, retrieval

router = APIRouter()

HISTORY_LIMIT = 6  # last N messages carried as context (QRY-6)


class QueryRequest(BaseModel):
    question: str
    workspace_id: str = "default"
    conversation_id: str | None = None


async def _get_or_create_conversation(db: AsyncSession, conversation_id: str | None, workspace_id: str) -> Conversation:
    if conversation_id:
        conv = await db.get(Conversation, conversation_id)
        if conv:
            return conv
    conv = Conversation(id=str(uuid.uuid4()), workspace_id=workspace_id)
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


@router.post("/")
async def query_documents(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    conv = await _get_or_create_conversation(db, req.conversation_id, req.workspace_id)
    history = await _history(db, conv.id)

    chunks = await retrieval.retrieve(db, req.workspace_id, req.question)

    db.add(Message(conversation_id=conv.id, role="user", content=req.question))

    if not chunks:
        answer, grounded, citations = generation.NOT_FOUND, False, []
    else:
        citations = generation.citations_from(chunks)
        grounded = True
        try:
            answer = generation.generate_answer(req.question, chunks, history)
            if generation.NOT_FOUND in answer:
                grounded, citations = False, []
        except Exception as e:
            # Retrieval succeeded; generation failed (missing/invalid key, rate limit).
            answer = (
                f"(Generation unavailable: {type(e).__name__}. Set a valid OPENROUTER_API_KEY.)\n\n"
                "Top retrieved context:\n\n"
                + "\n---\n".join(c["text"][:300] for c in chunks)
            )

    db.add(Message(conversation_id=conv.id, role="assistant", content=answer, citations=citations))

    return {
        "answer": answer,
        "citations": citations,
        "grounded": grounded,
        "workspace_id": req.workspace_id,
        "conversation_id": conv.id,
    }


@router.post("/stream")
async def query_stream(req: QueryRequest):
    """SSE token streaming (QRY-7): 'meta' (conversation_id + citations) -> 'delta'* -> 'done'.

    Persists the user + assistant messages so streaming supports multi-turn too.
    """

    async def gen():
        async with AsyncSessionLocal() as db:
            conv = await _get_or_create_conversation(db, req.conversation_id, req.workspace_id)
            history = await _history(db, conv.id)
            chunks = await retrieval.retrieve(db, req.workspace_id, req.question)
            db.add(Message(conversation_id=conv.id, role="user", content=req.question))
            await db.commit()

            if not chunks:
                yield {"event": "meta", "data": json.dumps(
                    {"conversation_id": conv.id, "grounded": False, "citations": []})}
                yield {"event": "delta", "data": generation.NOT_FOUND}
                db.add(Message(conversation_id=conv.id, role="assistant", content=generation.NOT_FOUND))
                await db.commit()
                yield {"event": "done", "data": "{}"}
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
            db.add(Message(
                conversation_id=conv.id, role="assistant", content=answer, citations=citations))
            await db.commit()
            yield {"event": "done", "data": "{}"}

    return EventSourceResponse(gen())
