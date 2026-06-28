import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Chunk, Document
from app.models.user import User
from app.models.workspace import Workspace
from app.services.auth import get_current_user
from app.services.queue import enqueue_ingest
from app.services.storage import delete_object, download_bytes, upload_bytes

router = APIRouter()


async def _resolve_workspace(workspace_id: str, user: User, db: AsyncSession) -> Workspace:
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.owner_id and ws.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your workspace")
    return ws


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _resolve_workspace(workspace_id, current_user, db)

    data = await file.read()
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        owner_id=current_user.id,
        filename=file.filename or "upload",
        mime_type=file.content_type,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    s3_key = f"{ws.id}/{doc.id}/{doc.filename}"
    upload_bytes(s3_key, data, file.content_type)

    task_id = enqueue_ingest(doc.id, ws.id, s3_key, doc.filename, file.content_type or "")

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "workspace_id": ws.id,
        "status": "pending",
        "task_id": task_id,
    }


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")

    s3_key = f"{doc.workspace_id}/{doc.id}/{doc.filename}"
    try:
        data, content_type = download_bytes(s3_key)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")

    s3_key = f"{doc.workspace_id}/{doc.id}/{doc.filename}"
    try:
        delete_object(s3_key)
    except Exception:
        pass
    chunks = await db.execute(select(Chunk).where(Chunk.document_id == doc_id))
    for chunk in chunks.scalars().all():
        await db.delete(chunk)
    await db.delete(doc)
    await db.commit()
    return {"deleted": doc_id}


@router.get("/documents")
async def list_documents(
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _resolve_workspace(workspace_id, current_user, db)
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == ws.id, Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return {
        "workspace_id": ws.id,
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
