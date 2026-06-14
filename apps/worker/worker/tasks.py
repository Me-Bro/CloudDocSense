import structlog

from worker.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def ingest_document(self, document_id: str, workspace_id: str, s3_key: str) -> dict:
    """Parse, chunk, embed, upsert a document. Full pipeline implemented in M1."""
    log.info("ingest_document.start", document_id=document_id, workspace_id=workspace_id)
    # M1: parse -> chunk -> embed -> upsert
    return {"document_id": document_id, "status": "pending_m1"}
