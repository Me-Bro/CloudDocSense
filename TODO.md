# DocSense — Todo List

---

## M0 — Spike (Weeks 1–2)
- [ ] Scaffold monorepo dirs + `pnpm` workspace + Python project (`uv`/Poetry)
- [ ] Write `docker-compose.yml` (postgres+pgvector, redis, minio)
- [ ] Write `infra/postgres/init.sql` — enable pgvector extension + HNSW index
- [ ] FastAPI skeleton: `/health`, config, DB session, Alembic init
- [ ] pgvector smoke test: embed 20 FAQ entries, cosine query, return best match
- [ ] React skeleton: chat shell + API client
- [ ] CI: lint + test + docker build on PR (`.github/workflows/ci.yml`)
- [ ] `Makefile`: `up`, `down`, `migrate`, `seed`, `test`, `lint`

---

## M1 — Core RAG (Weeks 3–6)
- [ ] File upload → MinIO storage + `documents` row + Celery job enqueue
- [ ] Ingestion: detect type (text/PDF/DOCX/image)
- [ ] Parse text + PDF → extract text
- [ ] Chunk via LlamaIndex semantic chunking (~500 tokens + overlap) + attach metadata
- [ ] Embed chunks (OpenAI `text-embedding-3-small`) → upsert to pgvector
- [ ] `RetrieverInterface` wrapping `LlamaIndex VectorStoreIndex` over `PGVectorStore`
- [ ] Top-k ANN + `workspace_id` filter (mandatory) + confidence threshold gate
- [ ] Grounded prompt: answer only from chunks, cite source+page per claim
- [ ] SSE streaming endpoint (`POST /query`)
- [ ] React chat view: streaming answers + message history
- [ ] React upload view: drag-drop + ingestion status
- [ ] Sources sidebar: citations per answer, click → view chunk/page
- [ ] "Not found" path when below confidence threshold

---

## M2 — Multimodal (Weeks 7–9)
- [ ] Vision parsing for scanned/image docs (Claude / GPT-4o class)
- [ ] Confidence score on vision parse; flag low-confidence for human review
- [ ] Few-shot JSON extraction prompts (QRY-5)
- [ ] UI: low-confidence review flag in upload view

---

## M3 — Agentic (Weeks 10–12)
- [ ] Query router: classify simple vs complex/multi-hop
- [ ] LangGraph agent: typed state, Postgres checkpointer, hard cap 5 steps, per-step timeout
- [ ] Allow-listed tools: `retrieve`, `summarise`, `extract_json`, `calc`
- [ ] Wrap LlamaIndex retriever as LangGraph tool
- [ ] Hard/comparison queries → reasoning model path
- [ ] Context manager: token budgeting (system + chunks + history)
- [ ] Long chat summarisation → `conversations.summary` (QRY-6)

---

## MVP Hardening (~Week 14)
- [ ] Closed beta with 3–5 partner teams
- [ ] Eval pipeline: `eval/golden_set/` (~100 Q/A/source triples)
- [ ] Retrieval hit-rate runner + LLM-as-judge answer correctness
- [ ] CI gate: grounding failure = release blocker
- [ ] Accuracy ≥85% on golden set; 100% citation/not-found coverage

---

## GA (~Week 24)
- [ ] Workspaces + RBAC (JWT, `workspace_id` scoping, admin/member/viewer roles)
- [ ] Cost dashboard (ADM-3): `usage_events` per-query token/cost metrics
- [ ] Drive / Notion ingestion connectors
- [ ] CI isolation test: assert zero cross-tenant chunk leakage
- [ ] 99.5% availability target + structured logging + request tracing

---

## Cross-Cutting (any phase)
- [ ] Alembic migrations for all tables
- [ ] `.env.example` documenting all vars
- [ ] `docker-compose.override.yml` for hot-reload dev
- [ ] Multi-stage Dockerfiles (prod: static web via nginx, api via gunicorn)
- [ ] Pre-commit hooks: ruff + mypy + eslint
- [ ] A/B router: quality + cost tracking for reasoning vs standard model path

---

## Open Questions (resolve before build)
- [ ] pgvector-only for GA, or plan Qdrant/Weaviate migration earlier?
- [ ] Which reasoning model + budget cap for hard-query path?
- [ ] Pricing model (per-seat / per-query / per-doc)?
- [ ] First two ingestion connectors (Drive / Notion / other)?
