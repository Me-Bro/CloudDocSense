# DocSense — Product Requirements Document

> **An AI Knowledge Assistant for Teams**
> *Ask questions across your documents, get cited answers, automate the busywork.*

---

| Field | Value |
|---|---|
| **Version** | 1.0 (Draft for review) |
| **Status** | Proposed — pre-build |
| **Document owner** | Product |
| **Date** | June 2026 |
| **Target launch** | MVP in ~14 weeks; GA in ~24 weeks |
| **Tech stack** | Python · FastAPI · LlamaIndex (retrieval) · LangGraph (agents) · pgvector · Anthropic & OpenAI APIs · React |

> **Scope note:** This PRD applies a focused subset of modern AI concepts — embeddings, vector search, RAG, multimodal document parsing, tool-using agents, context engineering, and reasoning models — to one coherent, shippable product. Not every concept from the learning plan is used; the selection is deliberate and tied to real user value.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Users & Use Cases](#3-users--use-cases)
4. [AI Concepts → Product Features](#4-ai-concepts--product-features)
5. [System Architecture](#5-system-architecture)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Roadmap & Milestones](#8-roadmap--milestones)
9. [Success Metrics & Evaluation](#9-success-metrics--evaluation)
10. [Future Work (Post-GA)](#10-future-work-post-ga)
11. [Risks & Mitigations](#11-risks--mitigations)

---

## 1. Overview

### 1.1 Problem

Teams accumulate knowledge across PDFs, contracts, wikis, support tickets, scanned invoices, and chat threads. Finding a specific answer means hunting through tools, opening a dozen documents, and re-reading content someone already wrote. Keyword search returns documents, not answers, and it fails when the user's words don't match the document's words. Generic chatbots, meanwhile, don't know anything about the team's private content and will confidently make things up.

### 1.2 Solution

DocSense is an AI knowledge assistant that ingests a team's documents, understands them semantically, and answers natural-language questions with citations back to the source. It goes beyond search: it can parse scanned and image-based documents, reason over multi-step questions, and take simple actions through tools (e.g., look up a figure, summarise a folder, draft a reply). Every answer shows its sources, so the team can trust it.

> 💡 **In one sentence:** DocSense turns a team's scattered documents into a single, trustworthy assistant that gives cited answers and automates routine lookups.

### 1.3 Why Now

- Embedding and reasoning models are now cheap and good enough to run this profitably at scale.
- Native multimodal models can read scanned documents and screenshots, removing the old OCR bottleneck.
- Mature open tooling (pgvector, LlamaIndex for retrieval, LangGraph for agents) means a small team can build production RAG in weeks, not quarters.

---

## 2. Goals & Non-Goals

### 2.1 Goals

1. Let a user ask a question in plain language and get an accurate, cited answer from their own documents in under 5 seconds.
2. Support text, PDF, and image/scanned documents out of the box.
3. Make answers trustworthy: every claim links to its source chunk, and the assistant says "I don't know" rather than guessing.
4. Ship an MVP a small team can run on a single Postgres instance, then scale the same architecture to a dedicated vector store.

### 2.2 Non-Goals (v1)

- Training or fine-tuning custom foundation models. v1 uses hosted and open models as-is.
- Real-time collaborative editing of documents. DocSense reads and answers; it does not replace the editor.
- On-device / fully offline deployment. Noted as a future track (see §10).
- General-purpose web agents that browse arbitrarily. Tool use in v1 is scoped and allow-listed.

---

## 3. Users & Use Cases

### 3.1 Target Users

| Persona | Context | Primary need |
|---|---|---|
| Operations / Support lead | Drowning in policy docs and tickets | Fast, cited answers to recurring questions |
| Legal / Finance analyst | Reviews contracts and invoices | Extract structured facts; parse scanned files |
| Knowledge worker (general) | Lots of internal wikis & PDFs | "Where is it written that…" answered instantly |
| Team admin | Owns the workspace | Control sources, access, and cost |

### 3.2 Key Use Cases

- **Ask-your-docs:** "What is our refund window for enterprise plans?" → cited answer pulled from the policy PDF.
- **Multi-step reasoning:** "Compare the SLA in the Acme contract with the Globex one and tell me which is stricter."
- **Document extraction:** Upload a scanned invoice → get vendor, date, line items, and total as structured JSON.
- **Summarise on demand:** "Summarise everything in the Q2 folder into five bullets."

---

## 4. AI Concepts → Product Features

> This is the heart of the PRD: each AI concept is tied to a concrete capability and a real user benefit. Concepts not listed here (e.g. fine-tuning, distillation, quantization, RLHF) are intentionally out of v1 scope and revisited in §10.

| AI Concept | How DocSense uses it | User-facing benefit |
|---|---|---|
| **Embeddings / Vectorization** | Every document chunk and every query is embedded into a vector. | Search by meaning, not keywords. |
| **Vector Database (pgvector)** | Stores chunk vectors with metadata; HNSW index for fast nearest-neighbour search. | Sub-second retrieval over millions of chunks. |
| **Retrieval-Augmented Generation** | Retrieve top-k relevant chunks, then have the LLM answer using only those. | Accurate answers grounded in the team's own data. |
| **Chunking + metadata filtering** | Semantic chunking; filter by source, date, owner before ranking. | Right scope, fewer wrong answers. |
| **Multimodal models** | Vision model reads scanned PDFs, invoices, and screenshots into text/JSON. | Works on scanned and image docs, not just clean text. |
| **Context engineering** | Token budgeting, summarisation of long chats, selective retrieval. | Long conversations stay coherent and cheap. |
| **AI Agents (tool use)** | A scoped ReAct loop with allow-listed tools (retrieve, summarise, extract, calc). | Handles multi-step questions, not just lookups. |
| **Reasoning models** | Hard / multi-hop questions routed to an extended-thinking model. | Better answers on comparisons and analysis. |
| **Few-shot prompting** | Few-shot examples drive structured extraction and answer formatting. | Reliable JSON output, no training required. |

> 🟢 **Design principle: grounded by default**
> The LLM never answers from its own memory about the team's data. If retrieval returns nothing relevant above a confidence threshold, DocSense responds with "I couldn't find this in your documents" instead of guessing. This single rule is what makes the product trustworthy.

---

## 5. System Architecture

### 5.1 High-Level Flow

Two pipelines: an **ingestion pipeline** (offline, when documents are added) and a **query pipeline** (online, when a user asks a question).

#### Ingestion pipeline

1. Upload → detect file type (text, PDF, image).
2. Parse: text extracted directly; scanned/image files sent to a multimodal model for extraction.
3. Chunk into ~500-token semantic pieces with overlap; attach metadata (source, page, owner, date).
4. Embed each chunk; upsert vectors + metadata into pgvector.

#### Query pipeline

1. Embed the user query.
2. Retrieve top-k chunks from pgvector (with metadata filters).
3. Router decides: simple lookup → standard model; complex/multi-step → agent loop and/or reasoning model.
4. Assemble context (system prompt + retrieved chunks + trimmed history) within the token budget.
5. Generate a grounded answer; attach citations to the chunks used; stream back to the UI.

### 5.2 Component Diagram

```
React UI (chat + upload + sources sidebar)
        ↓  ↑  (HTTP / SSE streaming)
FastAPI backend — Orchestrator
   ├─ Ingestion + Retrieval (LlamaIndex): parse → chunk → embed → pgvector ANN + filters
   ├─ Router (simple → standard model  |  hard → reasoning / agent)
   ├─ Agent loop (LangGraph): typed state, checkpointer, allow-listed tools, max 5 steps
   └─ Context manager (token budget + summarisation)
        ↓
PostgreSQL + pgvector  |  Object storage (files)  |  Model APIs (Anthropic / OpenAI / local)
```

### 5.3 Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **API / backend** | Python + FastAPI | Async, fast, first-class in the AI ecosystem. |
| **Retrieval / indexing** | LlamaIndex | Purpose-built RAG: hierarchical chunking, auto-merging, 300+ document connectors. |
| **Agent orchestration** | LangGraph | Graph-based agent loop with typed state + checkpointers for recovery & step caps. |
| **Vector store** | Postgres + pgvector (HNSW) | One database for app + vectors in MVP; production-grade up to ~10M vectors. |
| **Embeddings** | OpenAI text-embedding-3-small (or open model) | Cheap, strong quality, easy to swap. |
| **Generation** | Claude / GPT for answers; reasoning model for hard queries | Quality where it matters, cost control elsewhere. |
| **Multimodal parsing** | Native vision model (Claude / GPT-4o class) | Removes the legacy OCR pipeline. |
| **Queue / workers** | Celery or RQ + Redis | Background ingestion of large docs. |
| **Frontend** | React + streaming (SSE) | Live token streaming, sources sidebar. |

> 💡 **Why two frameworks, not one**
>
> LlamaIndex and LangGraph are complementary layers, not competing choices. LlamaIndex owns retrieval — its chunking, reranking, and document connectors are strongest there. LangGraph owns the agent loop, where its typed state and checkpointers give durable, recoverable multi-step execution. A LlamaIndex retrieval engine is wrapped as a LangGraph tool, so the layers compose cleanly. Both add some abstraction overhead (low single-digit milliseconds per step) — a non-issue at MVP scale, but a candidate to replace with a custom pipeline if we cross ~100K queries/day (tracked in §10).

> 💡 **pgvector migration path**
>
> The retrieval layer (LlamaIndex) is kept storage-agnostic from day one, so migrating to a dedicated vector store (Qdrant or Weaviate) is a config swap, not a rewrite. The concrete trigger: query P99 latency degrades or the corpus crosses ~10M vectors. At MVP scale, pgvector HNSW is competitive with purpose-built engines and eliminates an entire service from the stack.

---

## 6. Functional Requirements

> Requirements use MoSCoW priority. IDs are stable for tracking.

### 6.1 Ingestion

| ID | Requirement | Priority |
|---|---|---|
| ING-1 | Upload text, PDF, DOCX, and common image formats. | **Must** |
| ING-2 | Parse scanned/image documents via a multimodal model. | **Must** |
| ING-3 | Chunk documents semantically with configurable size & overlap. | **Must** |
| ING-4 | Store chunk embeddings + metadata in pgvector. | **Must** |
| ING-5 | Re-index when a source document changes. | Should |
| ING-6 | Connectors for Google Drive / Notion. | Could |

### 6.2 Query & Answering

| ID | Requirement | Priority |
|---|---|---|
| QRY-1 | Answer natural-language questions grounded in retrieved chunks. | **Must** |
| QRY-2 | Show citations (source, page) for every answer; click to view. | **Must** |
| QRY-3 | Return "not found" when confidence is below threshold. | **Must** |
| QRY-4 | Route complex questions to an agent / reasoning model. | Should |
| QRY-5 | Structured extraction to JSON via few-shot prompting. | Should |
| QRY-6 | Multi-turn chat with context summarisation on overflow. | **Must** |
| QRY-7 | Stream answers token-by-token to the UI. | Should |

### 6.3 Workspace & Admin

| ID | Requirement | Priority |
|---|---|---|
| ADM-1 | Per-workspace document isolation (metadata-scoped retrieval). | **Must** |
| ADM-2 | Role-based access (admin, member, viewer). | Should |
| ADM-3 | Usage & cost dashboard (tokens, queries, per-user). | Should |
| ADM-4 | Audit log of questions and sources returned. | Could |

---

## 7. Non-Functional Requirements

| Area | Target |
|---|---|
| **Latency** | Median answer < 5s for simple queries; < 12s for reasoning/agent queries. |
| **Accuracy** | ≥ 85% of answers judged correct & grounded on the eval set (see §9). |
| **Grounding** | 100% of answers either cite a source or explicitly say "not found." |
| **Scale (MVP)** | Up to 1M chunks on a single Postgres instance with HNSW. |
| **Cost** | Track $ per query; cheap model for routing/simple, premium only when needed. |
| **Privacy** | Per-workspace isolation; no cross-tenant retrieval; configurable data retention. |
| **Security** | Encryption at rest & in transit; allow-listed agent tools only. |
| **Availability** | 99.5% for query API at GA. |

---

## 8. Roadmap & Milestones

| Phase | Weeks | Deliverable | Concepts proven |
|---|---|---|---|
| **M0 — Spike** | 1–2 | Embeddings + cosine similarity demo; semantic FAQ matcher. | Embeddings, vector search |
| **M1 — Core RAG** | 3–6 | Upload → chunk → pgvector → cited answer (text/PDF). | RAG, vector DB, chunking |
| **M2 — Multimodal** | 7–9 | Scanned-doc parsing & JSON extraction. | Multimodal, few-shot |
| **M3 — Agentic** | 10–12 | Router + agent loop (LangGraph) + reasoning model for hard queries. | Agents, reasoning, context eng. |
| **MVP launch** | ~14 | Closed beta with 3–5 design-partner teams. | End-to-end |
| **GA** | ~24 | Workspaces, RBAC, cost dashboard, connectors. | Productionised |

> **Sequencing rationale:** Each milestone is independently demoable and de-risks the next. Core RAG (M1) is the product's spine; multimodal (M2) and agentic routing (M3) are additive layers that can be feature-flagged. This lets us launch a useful MVP at ~14 weeks even if M3 slips.

---

## 9. Success Metrics & Evaluation

### 9.1 Product Metrics

| Metric | Definition | Target (GA) |
|---|---|---|
| **Answer accuracy** | % answers correct & grounded on a held-out eval set. | ≥ 85% |
| **Citation rate** | % answers with a valid source link (or honest "not found"). | 100% |
| **Hallucination rate** | % answers with claims not supported by retrieved chunks. | < 3% |
| **Time-to-answer** | Median latency, simple queries. | < 5s |
| **Activation** | % new workspaces that ask ≥ 5 questions in week 1. | ≥ 60% |
| **Retention (W4)** | % of activated workspaces still querying at week 4. | ≥ 40% |
| **Cost per query** | Blended model + infra cost per answered query. | < $0.05 |

### 9.2 Evaluation Method

- Build a **golden eval set**: ~100 question/answer/source triples drawn from real partner documents.
- Run **automated grading** on every release: retrieval hit-rate (was the right chunk retrieved?) and answer correctness (LLM-as-judge + spot human review).
- **A/B the router**: measure quality and cost lift from sending hard queries to a reasoning model vs. always using the standard model.
- Track **grounding failures** explicitly — any unsupported claim is a release blocker.

---

## 10. Future Work (Post-GA)

> Concepts deliberately excluded from v1, with the trigger that would justify investing in them.

| Concept | Future use | Trigger to build |
|---|---|---|
| **Small Language Models + Quantization** | On-prem / offline deployment for privacy-sensitive customers. | Enterprise demand for no-cloud. |
| **Fine-tuning (LoRA/DPO)** | Adapt tone/format to a customer's domain. | Prompting plateaus on a vertical. |
| **Distillation** | Cheaper in-house model trained on our best answers. | Inference cost dominates margins. |
| **MCP server** | Expose DocSense retrieval as a tool to other assistants. | Partner/integration demand. |
| **Custom retrieval/agent pipeline** | Replace LlamaIndex + LangGraph abstractions with hand-rolled code. | Cross ~100K queries/day or hit framework bottlenecks. |
| **Advanced RAG (rerank, HyDE, multi-query)** | Lift retrieval quality on hard corpora. | Retrieval hit-rate stalls. |
| **pgvector → Qdrant/Weaviate migration** | Higher QPS, native hybrid search, stricter multi-tenancy. | Corpus > ~10M vectors or P99 latency degrades. |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Hallucinated answers erode trust. | 🔴 High | Grounded-by-default rule; "not found" fallback; citation on every claim. |
| Retrieval misses the relevant chunk. | 🔴 High | Tune chunking & k; add reranking (future); measure hit-rate continuously. |
| Model API cost spikes at scale. | 🟡 Med | Router sends only hard queries to premium models; cache; track $/query. |
| Scanned-doc parsing errors. | 🟡 Med | Confidence scoring on extraction; human-in-the-loop review for low confidence. |
| Agent loops / runaway tool calls. | 🟡 Med | Hard cap (5 steps); allow-listed tools; timeouts. |
| Data-privacy / tenant leakage. | 🔴 High | Strict per-workspace metadata filters; isolation tests in CI. |

---

## Open Questions for Review

- [ ] Build on pgvector only, or plan a dedicated vector store (Qdrant/Weaviate) for GA scale?
- [ ] Which reasoning model and budget cap for the "hard query" path?
- [ ] Pricing model: per-seat, per-query, or per-document-indexed?
- [ ] Which two ingestion connectors matter most to design partners?

---

*End of document · DocSense PRD v1.0 · Draft for review*
