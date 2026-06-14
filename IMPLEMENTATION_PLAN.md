# DocSense — Implementation Plan

> Engineering plan to build the product described in `DocSense_PRD.md`.
> **Stack:** Python · FastAPI · LlamaIndex · LangGraph · PostgreSQL + pgvector · Anthropic & OpenAI APIs · React · Celery/Redis · Docker.
> **Layout:** monorepo. **Status:** plan only, no code.

---

## 1. Guiding Principles

- **Grounded by default.** Retrieval gates generation. No relevant chunk above threshold → "not found". This rule is enforced in code, not prompts alone.
- **Storage-agnostic retrieval.** LlamaIndex vector store wrapped behind an interface. pgvector now, Qdrant/Weaviate later = config swap.
- **Two complementary frameworks.** LlamaIndex owns retrieval. LangGraph owns the agent loop. Retrieval engine exposed as a LangGraph tool.
- **Demoable milestones.** Each phase (M0–M3) ships independently; M2/M3 feature-flagged so MVP launches even if later phases slip.
- **Cost-aware routing.** Cheap model for simple/routing; premium/reasoning only when the router escalates.

---

## 2. Monorepo Layout

```
DocSense/
├── README.md
├── DocSense_PRD.md
├── IMPLEMENTATION_PLAN.md
├── docker-compose.yml              # full local stack
├── docker-compose.override.yml     # dev hot-reload
├── .env.example
├── Makefile                        # up / down / migrate / seed / test / lint
├── .github/workflows/ci.yml
│
├── apps/
│   ├── api/                        # FastAPI backend (orchestrator)
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   ├── app/
│   │   │   ├── main.py             # app factory, routers, SSE
│   │   │   ├── config.py           # pydantic-settings, env
│   │   │   ├── api/                # routes: ingest, query, workspace, admin, health
│   │   │   ├── core/               # auth, deps, errors, logging
│   │   │   ├── ingestion/          # parse → chunk → embed → upsert
│   │   │   ├── retrieval/          # LlamaIndex engine + store interface
│   │   │   ├── agents/             # LangGraph graph, tools, router
│   │   │   ├── context/            # token budget + history summarisation
│   │   │   ├── models/             # SQLAlchemy ORM
│   │   │   ├── schemas/            # pydantic DTOs
│   │   │   └── services/           # business logic
│   │   ├── alembic/                # DB migrations
│   │   └── tests/
│   │
│   ├── worker/                     # Celery workers (background ingestion)
│   │   ├── Dockerfile
│   │   └── worker/ tasks.py celery_app.py
│   │
│   └── web/                        # React frontend
│       ├── Dockerfile
│       ├── package.json
│       └── src/
│           ├── components/         # chat, upload, sources sidebar
│           ├── features/           # query, ingest, workspace
│           ├── lib/                # api client, SSE stream
│           └── pages/
│
├── packages/                       # shared code
│   ├── shared-py/                  # prompts, schemas, eval helpers (pip-installable)
│   └── shared-ts/                  # shared TS types (mirror of API DTOs)
│
├── infra/
│   ├── postgres/init.sql           # CREATE EXTENSION vector; HNSW
│   ├── docker/                     # base images, entrypoints
│   └── scripts/                    # seed, backup, healthchecks
│
└── eval/
    ├── golden_set/                 # ~100 Q/A/source triples
    ├── runners/                    # retrieval hit-rate, LLM-as-judge
    └── reports/
```

**Tooling.** Python: `uv` or Poetry, `ruff` + `mypy`, `pytest`. Web: `pnpm`, `vite`, `eslint`, `vitest`. Root `Makefile` + `pnpm` workspace orchestrate both. Pre-commit hooks for lint/format.

---

## 3. Data Model (PostgreSQL + pgvector)

| Table | Key columns | Notes |
|---|---|---|
| `workspaces` | id, name, settings(jsonb) | tenant root |
| `users` | id, email, role(admin/member/viewer) | RBAC |
| `memberships` | user_id, workspace_id, role | M:N |
| `documents` | id, workspace_id, filename, mime, status, source, owner, created_at | ingestion state machine |
| `chunks` | id, document_id, workspace_id, text, page, metadata(jsonb), `embedding vector(1536)` | HNSW index, **workspace_id filter mandatory** |
| `conversations` | id, workspace_id, user_id, summary | rolling summary for context mgmt |
| `messages` | id, conversation_id, role, content, citations(jsonb), tokens, cost | audit + cost |
| `ingestion_jobs` | id, document_id, state, error, attempts | Celery job tracking |
| `usage_events` | id, workspace_id, user_id, model, tokens_in/out, cost, query_type | cost dashboard |
| `audit_log` | id, workspace_id, question, sources(jsonb), ts | ADM-4 |

- **Index:** `CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);` partial/composite with `workspace_id` for tenant isolation.
- **Tenant safety:** every retrieval query filters `workspace_id`. CI isolation test asserts no cross-tenant leakage (Risk mitigation).
- Embedding dim configurable (1536 for `text-embedding-3-small`); store model name per chunk for safe re-embed/migration.

---

## 4. Backend Modules (FastAPI)

### 4.1 Ingestion pipeline (`ingestion/`)
1. **Upload** → store raw file in object storage (MinIO local / S3 prod), create `documents` row, enqueue Celery job.
2. **Detect type** → text / PDF / DOCX / image.
3. **Parse** → text extracted directly; scanned/image → multimodal vision model (Claude / GPT-4o class) → text/JSON. Confidence score; low confidence flagged for human review.
4. **Chunk** → LlamaIndex semantic chunking ~500 tokens + overlap; attach metadata (source, page, owner, date).
5. **Embed** → batch embed (OpenAI `text-embedding-3-small`, swappable).
6. **Upsert** → vectors + metadata into pgvector. Update doc status.
7. **Re-index (ING-5)** → on source change, diff + re-embed changed chunks.

### 4.2 Retrieval (`retrieval/`)
- LlamaIndex `VectorStoreIndex` over a `PGVectorStore`, hidden behind `RetrieverInterface` (swap to Qdrant/Weaviate later).
- Top-k ANN + metadata filters (workspace, source, date, owner).
- Confidence threshold gate → emits "not found" when below.

### 4.3 Router + Agents (`agents/`)
- **Router:** classify query simple vs complex/multi-hop. Simple → standard model RAG. Complex → LangGraph agent / reasoning model.
- **LangGraph agent:** typed state, checkpointer (Postgres), allow-listed tools, **hard cap 5 steps**, per-step timeout.
- **Tools (allow-listed):** `retrieve`, `summarise`, `extract_json`, `calc`. LlamaIndex retriever wrapped as a tool.
- **Reasoning path:** hard/comparison queries routed to extended-thinking model.

### 4.4 Context manager (`context/`)
- Token budgeting: system prompt + retrieved chunks + trimmed history within budget.
- Long chats → summarise older turns into `conversations.summary` (QRY-6).

### 4.5 Generation + Answer assembly
- Grounded prompt: answer **only** from retrieved chunks; cite source+page per claim (QRY-2).
- Few-shot prompts for structured JSON extraction (QRY-5).
- **SSE streaming** token-by-token to UI (QRY-7).

### 4.6 API surface
- `POST /ingest` (upload), `GET /documents`, `POST /query` (SSE), `GET/POST /workspaces`, `GET /admin/usage`, `GET /health`.
- Auth: JWT, workspace-scoped; RBAC middleware (ADM-2).

---

## 5. Frontend (React)

- **Chat view:** streaming answers (SSE), message history.
- **Sources sidebar:** citations per answer; click → view source chunk/page.
- **Upload view:** drag-drop, ingestion status, low-confidence review flag.
- **Admin:** usage/cost dashboard (ADM-3), member roles.
- Stack: React + Vite, TanStack Query, SSE client, Tailwind. Shared TS types from `packages/shared-ts`.

---

## 6. Docker & Local Stack

`docker-compose.yml` services:

| Service | Image / build | Purpose |
|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | app DB + vectors; `init.sql` enables extension + HNSW |
| `redis` | `redis:7` | Celery broker + result backend |
| `minio` | `minio/minio` | S3-compatible object storage (local files) |
| `api` | `apps/api/Dockerfile` | FastAPI, uvicorn, depends_on postgres/redis/minio |
| `worker` | `apps/worker/Dockerfile` | Celery worker for ingestion |
| `web` | `apps/web/Dockerfile` | React dev server / static build |
| `migrate` | api image, one-shot | runs Alembic on startup |

- **Dev:** `docker-compose.override.yml` mounts source for hot-reload (uvicorn `--reload`, vite dev).
- **Prod:** multi-stage Dockerfiles; web built to static + served via nginx; api behind gunicorn/uvicorn workers.
- Secrets/config via `.env` (model API keys, DB URL, etc). `.env.example` documents all vars.
- `Makefile`: `make up`, `make migrate`, `make seed`, `make eval`, `make test`.

---

## 7. Phased Delivery (maps to PRD §8)

| Phase | Weeks | Build | Exit criteria |
|---|---|---|---|
| **M0 — Spike** | 1–2 | Monorepo skeleton, docker-compose, pgvector up, embed + cosine demo, semantic FAQ matcher | embeddings retrieve correct FAQ; stack runs via `make up` |
| **M1 — Core RAG** | 3–6 | Ingestion (text/PDF) → chunk → pgvector → grounded cited answer; SSE; basic React chat+upload | upload doc, ask question, get cited answer < 5s; "not found" path works |
| **M2 — Multimodal** | 7–9 | Vision parsing of scanned/image docs; few-shot JSON extraction; confidence + review flag | scanned invoice → structured JSON; flagged low-confidence |
| **M3 — Agentic** | 10–12 | Router + LangGraph agent (5-step cap, checkpointer, allow-listed tools); reasoning model for hard queries; context summarisation | multi-hop comparison answered correctly; agent capped/timed-out safely |
| **MVP** | ~14 | Harden, closed beta with 3–5 partner teams; eval pipeline green | accuracy ≥85% on golden set; 100% citation/not-found |
| **GA** | ~24 | Workspaces, RBAC, cost dashboard, Drive/Notion connectors, 99.5% availability | NFR targets met; isolation tests in CI |

---

## 8. Evaluation (PRD §9)

- `eval/golden_set/`: ~100 Q/A/source triples from partner docs.
- `eval/runners/`: **retrieval hit-rate** (right chunk retrieved?) + **answer correctness** (LLM-as-judge + spot human).
- Run on every release in CI; **grounding failure = release blocker**.
- A/B router: quality + cost lift of reasoning path vs standard model.
- Track per-query cost from `usage_events`.

---

## 9. Cross-Cutting Concerns

| Concern | Approach |
|---|---|
| **Tenant isolation** | Mandatory `workspace_id` filter; CI isolation test (Risk 🔴). |
| **Security** | TLS in transit, encryption at rest; allow-listed tools only; JWT + RBAC. |
| **Cost control** | Router → cheap model default; cache; premium only on escalation; `$/query` tracked. |
| **Observability** | Structured logging, request tracing, per-query token/cost metrics, agent step traces. |
| **Reliability** | Celery retries + dead-letter; LangGraph checkpointer recovery; idempotent upserts. |
| **Config-driven swap** | Embedding model, generation model, vector store all env/config selectable. |

---

## 10. Open Questions (from PRD — resolve before/during build)

- [ ] pgvector-only for GA, or plan Qdrant/Weaviate migration earlier?
- [ ] Which reasoning model + budget cap for the hard-query path?
- [ ] Pricing model (per-seat / per-query / per-doc) — affects usage metering design.
- [ ] First two ingestion connectors (Drive / Notion / other)?

---

## 11. First Concrete Steps (M0)

1. Scaffold monorepo dirs + `pnpm` workspace + Python project (`uv`/Poetry).
2. Write `docker-compose.yml` (postgres+pgvector, redis, minio) + `init.sql`.
3. FastAPI skeleton: `/health`, config, DB session, Alembic init.
4. pgvector smoke test: embed 20 FAQ entries, cosine query, return best match.
5. React skeleton: chat shell + API client.
6. CI: lint + test + docker build on PR.

---

*Plan derived from DocSense PRD v1.0 · no application code written.*
