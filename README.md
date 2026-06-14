# DocSense

AI-powered document intelligence — RAG pipeline with grounded, cited answers.

**Stack:** Python · FastAPI · LlamaIndex · LangGraph · PostgreSQL + pgvector · Anthropic & OpenAI APIs · React · Celery/Redis · Docker

## Quick Start

```bash
cp .env.example .env          # fill in API keys
make up                        # start all services
make migrate                   # run DB migrations
```

API: http://localhost:8000  
Web: http://localhost:3000  
MinIO: http://localhost:9001 (minioadmin/minioadmin)

## Development

```bash
make up        # start stack (hot-reload via override)
make test      # run all tests
make lint      # run ruff + mypy + eslint
make eval      # run evaluation pipeline
make logs      # tail all service logs
make shell-db  # psql into postgres
```

## M0 Smoke Test (pgvector)

```bash
# requires postgres running + OPENAI_API_KEY
DATABASE_URL_SYNC=postgresql://docsense:docsense@localhost:5432/docsense \
OPENAI_API_KEY=sk-... \
python -m scripts.smoke_test_pgvector
```

## Project Status

| Phase | Status |
|-------|--------|
| M0 — Spike | Scaffolded |
| M1 — Core RAG | Planned |
| M2 — Multimodal | Planned |
| M3 — Agentic | Planned |

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) and [TODO.md](TODO.md).
