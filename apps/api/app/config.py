from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://docsense:docsense@localhost:5432/docsense"
    database_url_sync: str = "postgresql://docsense:docsense@localhost:5432/docsense"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Object storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "docsense-docs"

    # AI — generation via OpenRouter (OpenAI-compatible), embeddings local by default
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # OpenRouter (free-tier generation + vision)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    generation_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    vision_model: str = "meta-llama/llama-3.2-11b-vision-instruct:free"

    # Embeddings — "local" (fastembed, free/offline) or "openai"
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_confidence_threshold: float = 0.3

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440


settings = Settings()
