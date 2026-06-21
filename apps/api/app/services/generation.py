"""Grounded answer generation from retrieved chunks (OpenRouter)."""
from app.config import settings
from app.services.llm import chat, get_client

NOT_FOUND = "I could not find an answer in the provided documents."

SYSTEM = """You are DocSense, an AI assistant that answers questions ONLY from the provided document chunks.

Rules:
- Answer ONLY from the retrieved chunks below.
- Cite the source filename and page for every factual claim, e.g. (Source: policy.pdf, p.3).
- If the chunks do not contain enough information, respond exactly:
  "I could not find an answer in the provided documents."
- Never speculate or use outside knowledge."""


def _format_chunks(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        loc = f"{c['filename']}" + (f", p.{c['page']}" if c.get("page") is not None else "")
        blocks.append(f"[{i}] (Source: {loc})\n{c['text']}")
    return "\n\n".join(blocks)


def build_messages(question: str, chunks: list[dict], history: list[dict] | None = None) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    if history:
        msgs.extend(history)
    user = f"Retrieved chunks:\n{_format_chunks(chunks)}\n\nQuestion: {question}\n\nAnswer (with citations):"
    msgs.append({"role": "user", "content": user})
    return msgs


def citations_from(chunks: list[dict]) -> list[dict]:
    return [
        {"source": c["filename"], "page": c.get("page"), "chunk_id": c["chunk_id"]}
        for c in chunks
    ]


def generation_available() -> bool:
    return bool(settings.openrouter_api_key or settings.openai_api_key)


def generate_answer(question: str, chunks: list[dict], history: list[dict] | None = None) -> str:
    return chat(build_messages(question, chunks, history))


def stream_answer(question: str, chunks: list[dict], history: list[dict] | None = None):
    """Yield answer text deltas from the OpenRouter stream."""
    stream = get_client().chat.completions.create(
        model=settings.generation_model,
        messages=build_messages(question, chunks, history),
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta
