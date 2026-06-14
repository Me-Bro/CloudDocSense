from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db),
):
    # M1: store to MinIO + enqueue Celery job
    return {
        "filename": file.filename,
        "workspace_id": workspace_id,
        "status": "pending",
        "message": "Ingestion pipeline not yet implemented (M1)",
    }


@router.get("/documents")
async def list_documents(workspace_id: str = "default", db: AsyncSession = Depends(get_db)):
    return {"documents": [], "workspace_id": workspace_id}
