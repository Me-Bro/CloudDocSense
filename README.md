# DocSense

AI-powered document intelligence — RAG pipeline with grounded, cited answers.

**Stack:** Python · FastAPI · LlamaIndex · LangGraph · PostgreSQL + pgvector · OpenRouter · React · Celery/Redis · Docker

## Quick Start

```bash
cp .env.example .env          # fill in API keys (OpenRouter required; others optional)
docker compose up -d          # start all services
docker compose run --rm migrate  # run DB migrations (first time only)
```

**Services:**

| Service | URL | Credentials |
|---------|-----|-------------|
| Web UI | http://localhost:3000 | — |
| API | http://localhost:8000 | — |
| API Docs (Swagger) | http://localhost:8000/docs | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

## AI / Embedding Config

Free-tier path (default — no paid key needed):

```env
EMBEDDING_PROVIDER=local          # fastembed, runs offline (dim=384)
OPENROUTER_API_KEY=<your-key>     # free models via openrouter.ai/keys
GENERATION_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
VISION_MODEL=meta-llama/llama-3.2-11b-vision-instruct:free
```

Paid path: set `EMBEDDING_PROVIDER=openai` and supply `OPENAI_API_KEY`.

## Development

```bash
docker compose up -d   # start stack (API has hot-reload)
make test              # run all tests
make lint              # ruff + mypy + eslint
make eval              # run evaluation pipeline
make logs              # tail all service logs
make shell-db          # psql into postgres
```

## Project Status

| Phase | Status |
|-------|--------|
| M0 — Spike | Done |
| M1 — Core RAG | In progress |
| M2 — Multimodal | Planned |
| M3 — Agentic | Planned |

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) and [TODO.md](TODO.md).
