"""Provider-agnostic embeddings.

- "local": fastembed (ONNX, no torch) — free, runs offline. Default model
  BAAI/bge-small-en-v1.5 (dim 384).
- "openai": OpenAI embeddings API (e.g. text-embedding-3-small, dim 1536).

Switch via EMBEDDING_PROVIDER / EMBEDDING_MODEL / EMBEDDING_DIM in .env.
The dim MUST match the chunks.embedding pgvector column (see migrations).
"""
from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def _local_model():
    # Imported lazily so the openai path doesn't pay the fastembed import cost.
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts -> list of float vectors (dim = settings.embedding_dim)."""
    if settings.embedding_provider == "local":
        return [vec.tolist() for vec in _local_model().embed(texts)]

    if settings.embedding_provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model=settings.embedding_model, input=texts)
        return [e.embedding for e in resp.data]

    raise ValueError(f"Unknown embedding_provider: {settings.embedding_provider!r}")


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
