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

    # Groq (free-tier, fast inference) — get key at https://console.groq.com/keys
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Cerebras (free-tier, wafer-scale ~2000 tok/s) — get key at https://cloud.cerebras.ai
    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"

    # Mistral AI (free-tier, rate limited) — get key at https://console.mistral.ai/api-keys
    mistral_api_key: str = ""
    mistral_base_url: str = "https://api.mistral.ai/v1"

    generation_model: str = "qwen/qwen3-next-80b-a3b-instruct:free"
    # Fallback chain (comma-separated, "provider>model_id" format).
    # No prefix = openrouter. Tried in order on 429/404/502/503.
    generation_models: str = (
        # OpenRouter — large free models
        "qwen/qwen3-next-80b-a3b-instruct:free,"
        "openai/gpt-oss-120b:free,"
        "qwen/qwen3-coder:free,"
        "nex-agi/nex-n2-pro:free,"
        # Groq — fast free inference
        "groq>llama-3.3-70b-versatile,"
        "groq>qwen/qwen3.6-27b,"
        # Cerebras — wafer-scale, extremely fast free inference
        "cerebras>llama-3.3-70b,"
        "cerebras>qwen-3-32b,"
        # OpenRouter — mid-size free models
        "google/gemma-4-31b-it:free,"
        "google/gemma-4-26b-a4b-it:free,"
        "meta-llama/llama-3.3-70b-instruct:free,"
        "nvidia/nemotron-3-super-120b-a12b:free,"
        "nvidia/nemotron-3-ultra-550b-a55b:free,"
        "nousresearch/hermes-3-llama-3.1-405b:free,"
        "openai/gpt-oss-20b:free,"
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free,"
        "nvidia/nemotron-3-nano-30b-a3b:free,"
        # Groq — small fast fallback
        "groq>llama-3.1-8b-instant,"
        # Mistral — free tier (rate limited)
        "mistral>mistral-small-latest,"
        "mistral>open-mistral-nemo,"
        # Cerebras — small fast fallback
        "cerebras>llama-3.1-8b,"
        # OpenRouter — small fallbacks
        "nvidia/nemotron-nano-9b-v2:free,"
        "meta-llama/llama-3.2-3b-instruct:free"
    )
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
