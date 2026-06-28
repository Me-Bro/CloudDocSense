import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.services.auth import get_current_user

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str


@router.get("/")
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workspace).where(Workspace.owner_id == current_user.id)
    )
    workspaces = result.scalars().all()
    return {
        "workspaces": [
            {"id": ws.id, "name": ws.name, "settings": ws.settings}
            for ws in workspaces
        ]
    }


@router.post("/", status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = Workspace(id=str(uuid.uuid4()), name=body.name, owner_id=current_user.id)
    db.add(ws)
    await db.flush()
    return {"id": ws.id, "name": ws.name}


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your workspace")
    await db.delete(ws)
    return {"deleted": workspace_id}
