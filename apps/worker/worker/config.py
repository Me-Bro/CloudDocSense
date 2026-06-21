"""Worker settings — read from env (env_file=.env in compose).

Self-contained: the worker package does not import the api `app` package.
"""
import os


class WorkerSettings:
    # Database (sync — Celery tasks are synchronous)
    database_url_sync: str = os.environ.get(
        "DATABASE_URL_SYNC", "postgresql://docsense:docsense@localhost:5432/docsense"
    )

    # Object storage
    s3_endpoint_url: str = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
    s3_access_key: str = os.environ.get("S3_ACCESS_KEY", "minioadmin")
    s3_secret_key: str = os.environ.get("S3_SECRET_KEY", "minioadmin")
    s3_bucket: str = os.environ.get("S3_BUCKET", "docsense-docs")

    # Embeddings — must match the chunks.embedding pgvector column dim
    embedding_provider: str = os.environ.get("EMBEDDING_PROVIDER", "local")
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    embedding_dim: int = int(os.environ.get("EMBEDDING_DIM", "384"))

    # Chunking (token-approx via words: ~1.3 words/token)
    chunk_target_tokens: int = int(os.environ.get("CHUNK_TARGET_TOKENS", "500"))
    chunk_overlap_tokens: int = int(os.environ.get("CHUNK_OVERLAP_TOKENS", "50"))


settings = WorkerSettings()
