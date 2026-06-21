"""Celery task dispatch from the API (by name — api doesn't import the worker pkg)."""
from functools import lru_cache

from celery import Celery

from app.config import settings


@lru_cache(maxsize=1)
def _celery() -> Celery:
    return Celery("docsense-api", broker=settings.celery_broker_url, backend=settings.celery_result_backend)


def enqueue_ingest(
    document_id: str, workspace_id: str, s3_key: str, filename: str, mime_type: str
) -> str:
    result = _celery().send_task(
        "worker.tasks.ingest_document",
        args=[document_id, workspace_id, s3_key, filename, mime_type],
    )
    return result.id
