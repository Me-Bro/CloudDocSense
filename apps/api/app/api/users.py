from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.search_history import SearchHistory
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()


@router.get("/me/search-history")
async def get_search_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": h.id,
                "query": h.query_text,
                "workspace_id": h.workspace_id,
                "result_count": h.result_count,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in items
        ]
    }


@router.delete("/me/search-history/{entry_id}")
async def delete_search_history_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SearchHistory).where(
            SearchHistory.id == entry_id,
            SearchHistory.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    return {"deleted": entry_id}


@router.delete("/me/search-history")
async def clear_search_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(SearchHistory).where(SearchHistory.user_id == current_user.id))
    return {"cleared": True}
