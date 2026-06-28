import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversation, Message
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()
log = structlog.get_logger()


@router.get("/")
async def list_conversations(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    convs = result.scalars().all()

    # fetch first user message per conversation for preview
    items = []
    for c in convs:
        preview_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == c.id, Message.role == "user")
            .order_by(Message.created_at)
            .limit(1)
        )
        first_msg = preview_result.scalar_one_or_none()
        items.append({
            "id": c.id,
            "workspace_id": c.workspace_id,
            "preview": (first_msg.content[:80] if first_msg else "Empty conversation"),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"conversations": items}


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your conversation")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations or [],
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your conversation")

    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conv)
    return {"deleted": conversation_id}
