"""Sync DB access for the ingest pipeline (psycopg2 + pgvector)."""
import uuid
from contextlib import contextmanager

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json, execute_values

from worker.config import settings


@contextmanager
def get_conn():
    conn = psycopg2.connect(settings.database_url_sync)
    try:
        register_vector(conn)
        yield conn
    finally:
        conn.close()


def set_document_status(conn, document_id: str, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE documents SET status = %s WHERE id = %s", (status, document_id)
        )
    conn.commit()


def replace_chunks(
    conn,
    document_id: str,
    workspace_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    embedding_model: str,
) -> int:
    """Delete existing chunks for the doc, then bulk-insert new ones. Returns count."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
        rows = [
            (
                str(uuid.uuid4()),
                document_id,
                workspace_id,
                c["text"],
                c["page"],
                Json({"chunk_index": c["chunk_index"]}),
                embedding_model,
                emb,
            )
            for c, emb in zip(chunks, embeddings)
        ]
        execute_values(
            cur,
            """
            INSERT INTO chunks
              (id, document_id, workspace_id, text, page, chunk_metadata,
               embedding_model, embedding)
            VALUES %s
            """,
            rows,
            template="(%s, %s, %s, %s, %s, %s, %s, %s)",
        )
    conn.commit()
    return len(rows)
