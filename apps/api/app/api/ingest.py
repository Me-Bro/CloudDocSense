import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document
from app.services.queue import enqueue_ingest
from app.services.storage import upload_bytes

router = APIRouter()


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        filename=file.filename or "upload",
        mime_type=file.content_type,
        status="pending",
    )
    db.add(doc)
    await db.flush()  # assign/confirm id before commit

    s3_key = f"{workspace_id}/{doc.id}/{doc.filename}"
    upload_bytes(s3_key, data, file.content_type)

    task_id = enqueue_ingest(
        doc.id, workspace_id, s3_key, doc.filename, file.content_type or ""
    )

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "workspace_id": workspace_id,
        "status": "pending",
        "task_id": task_id,
    }


@router.get("/documents")
async def list_documents(workspace_id: str = "default", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return {
        "workspace_id": workspace_id,
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "mime_type": d.mime_type,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    }
