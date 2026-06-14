from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str


@router.get("/")
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    return {"workspaces": []}


@router.post("/")
async def create_workspace(body: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    return {"id": "placeholder", "name": body.name, "message": "RBAC not yet implemented (GA)"}
