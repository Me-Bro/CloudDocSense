"""Vector retrieval over pgvector — workspace-scoped, cosine similarity.

Returns chunks above the confidence threshold. Empty result => the caller
should answer "not found" rather than generate (grounded-by-default).
"""
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.embeddings import embed_query

log = structlog.get_logger()


def _vec_literal(vec: list[float]) -> str:
    """pgvector text literal: [0.1,0.2,...] — cast with ::vector in SQL."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


async def retrieve(
    db: AsyncSession,
    workspace_id: str,
    query: str,
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[dict]:
    k = top_k or settings.retrieval_top_k
    thr = settings.retrieval_confidence_threshold if threshold is None else threshold
    log.info("retrieval.embed_query", workspace_id=workspace_id, query=query[:80], top_k=k, threshold=thr)
    qvec = _vec_literal(embed_query(query))

    sql = text(
        """
        SELECT c.id, c.text, c.page, c.document_id, d.filename,
               1 - (c.embedding <=> (:q)::vector) AS similarity
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :ws AND c.embedding IS NOT NULL
        ORDER BY c.embedding <=> (:q)::vector
        LIMIT :k
        """
    )
    result = await db.execute(sql, {"q": qvec, "ws": workspace_id, "k": k})
    rows = [
        {
            "chunk_id": r.id,
            "text": r.text,
            "page": r.page,
            "document_id": r.document_id,
            "filename": r.filename,
            "similarity": float(r.similarity),
        }
        for r in result
    ]
    kept = [r for r in rows if r["similarity"] >= thr]
    log.info(
        "retrieval.done",
        retrieved=len(rows),
        kept=len(kept),
        top_sim=round(rows[0]["similarity"], 3) if rows else None,
        sources=[r["filename"] for r in kept],
    )
    return kept
