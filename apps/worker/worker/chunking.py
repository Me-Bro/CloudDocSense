"""Sentence-aware chunking with overlap.

Token budgets are approximated by word count (~1.3 words per token for English).
Splits on sentence boundaries, packs sentences up to the target, and carries an
overlap tail into the next chunk so context isn't cut mid-thought.
"""
import re

from worker.config import settings

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_WORDS_PER_TOKEN = 1.3


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def chunk_text(text: str, page: int | None = None) -> list[dict]:
    """Return chunk dicts: {text, page, chunk_index}."""
    target_words = max(1, int(settings.chunk_target_tokens * _WORDS_PER_TOKEN))
    overlap_words = max(0, int(settings.chunk_overlap_tokens * _WORDS_PER_TOKEN))

    sentences = _split_sentences(text)
    chunks: list[dict] = []
    cur: list[str] = []
    cur_words = 0

    def flush():
        nonlocal cur, cur_words
        if not cur:
            return
        chunks.append({"text": " ".join(cur).strip(), "page": page, "chunk_index": len(chunks)})
        # carry overlap tail
        if overlap_words:
            tail, count = [], 0
            for s in reversed(cur):
                w = len(s.split())
                if count + w > overlap_words:
                    break
                tail.insert(0, s)
                count += w
            cur, cur_words = tail, count
        else:
            cur, cur_words = [], 0

    for sent in sentences:
        w = len(sent.split())
        if cur_words + w > target_words and cur:
            flush()
        cur.append(sent)
        cur_words += w
    if cur:
        chunks.append({"text": " ".join(cur).strip(), "page": page, "chunk_index": len(chunks)})

    return [c for c in chunks if c["text"]]


def chunk_segments(segments: list[tuple[int | None, str]]) -> list[dict]:
    """Chunk each (page, text) segment; re-number chunk_index globally."""
    out: list[dict] = []
    for page, text in segments:
        for c in chunk_text(text, page=page):
            c["chunk_index"] = len(out)
            out.append(c)
    return out
