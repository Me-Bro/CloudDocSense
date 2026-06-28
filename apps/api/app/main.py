import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.api import auth, conversations, health, ingest, query, users, workspaces
from app.database import AsyncSessionLocal

log = structlog.get_logger()


async def _cleanup_expired_guests() -> None:
    from app.models import Chunk, Document
    from app.models.conversation import Conversation
    from app.models.search_history import SearchHistory
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.services.storage import delete_object

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(User).where(User.is_guest == True, User.guest_expires_at < now)  # noqa: E712
        )
        expired = result.scalars().all()
        if not expired:
            return

        for user in expired:
            log.info("guest.cleanup", user_id=user.id)
            docs_result = await db.execute(select(Document).where(Document.owner_id == user.id))
            docs = docs_result.scalars().all()
            for doc in docs:
                chunks_result = await db.execute(select(Chunk).where(Chunk.document_id == doc.id))
                for chunk in chunks_result.scalars().all():
                    await db.delete(chunk)
                try:
                    delete_object(f"{doc.workspace_id}/{doc.id}/{doc.filename}")
                except Exception:
                    pass
                await db.delete(doc)

            convs_result = await db.execute(
                select(Conversation).where(Conversation.user_id == user.id)
            )
            for conv in convs_result.scalars().all():
                from app.models.conversation import Message
                msgs_result = await db.execute(
                    select(Message).where(Message.conversation_id == conv.id)
                )
                for msg in msgs_result.scalars().all():
                    await db.delete(msg)
                await db.delete(conv)

            ws_result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
            for ws in ws_result.scalars().all():
                await db.delete(ws)

            await db.delete(user)

        await db.commit()
        log.info("guest.cleanup.done", purged=len(expired))


async def _guest_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(1800)
        try:
            await _cleanup_expired_guests()
        except Exception as exc:
            log.warning("guest.cleanup.error", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.app_env)
    cleanup_task = asyncio.create_task(_guest_cleanup_loop())
    yield
    cleanup_task.cancel()
    log.info("shutdown")


app = FastAPI(
    title="DocSense API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
