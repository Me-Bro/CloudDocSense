"""Local fastembed embeddings (free/offline). Mirrors app.services.embeddings.

The worker is a separate package, so this is intentionally duplicated rather
than imported from the api `app` package. Dim must match the pgvector column.
"""
from functools import lru_cache

from worker.config import settings


@lru_cache(maxsize=1)
def _local_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if settings.embedding_provider == "local":
        return [vec.tolist() for vec in _local_model().embed(texts)]

    if settings.embedding_provider == "openai":
        import os

        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = client.embeddings.create(model=settings.embedding_model, input=texts)
        return [e.embedding for e in resp.data]

    raise ValueError(f"Unknown embedding_provider: {settings.embedding_provider!r}")
