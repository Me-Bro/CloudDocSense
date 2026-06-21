import structlog

from worker.celery_app import celery_app
from worker.chunking import chunk_segments
from worker.config import settings
from worker.db import get_conn, replace_chunks, set_document_status
from worker.embeddings import embed_texts
from worker.parsing import UnsupportedFileType, parse
from worker.storage import download_bytes

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def ingest_document(
    self, document_id: str, workspace_id: str, s3_key: str, filename: str = "", mime_type: str = ""
) -> dict:
    """M1 ingest: fetch -> parse -> chunk -> embed -> upsert into pgvector.

    Document.status transitions: pending -> processing -> indexed | failed | unsupported.
    """
    log.info("ingest.start", document_id=document_id, workspace_id=workspace_id, s3_key=s3_key)

    with get_conn() as conn:
        set_document_status(conn, document_id, "processing")
        try:
            data = download_bytes(s3_key)
            log.info("ingest.fetched", document_id=document_id, bytes=len(data))

            segments = parse(filename or s3_key, mime_type, data)
            log.info("ingest.parsed", document_id=document_id, segments=len(segments))

            chunks = chunk_segments(segments)
            log.info("ingest.chunked", document_id=document_id, chunks=len(chunks))

            if not chunks:
                set_document_status(conn, document_id, "indexed")
                log.warning("ingest.empty", document_id=document_id)
                return {"document_id": document_id, "status": "indexed", "chunks": 0}

            embeddings = embed_texts([c["text"] for c in chunks])
            log.info(
                "ingest.embedded",
                document_id=document_id,
                vectors=len(embeddings),
                model=settings.embedding_model,
            )

            count = replace_chunks(
                conn, document_id, workspace_id, chunks, embeddings, settings.embedding_model
            )
            log.info("ingest.upserted", document_id=document_id, chunks=count)
            set_document_status(conn, document_id, "indexed")
            log.info("ingest.done", document_id=document_id, chunks=count)
            return {"document_id": document_id, "status": "indexed", "chunks": count}

        except UnsupportedFileType as e:
            set_document_status(conn, document_id, "unsupported")
            log.warning("ingest.unsupported", document_id=document_id, error=str(e))
            return {"document_id": document_id, "status": "unsupported", "error": str(e)}

        except Exception as e:
            set_document_status(conn, document_id, "failed")
            log.error("ingest.failed", document_id=document_id, error=str(e))
            raise self.retry(exc=e)
