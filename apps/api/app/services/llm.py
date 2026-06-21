"""LLM client — OpenRouter (OpenAI-compatible) with a free-model fallback chain.

OpenRouter free (":free") models are frequently rate-limited upstream (429) or
temporarily unavailable (404). We try a list of free models in order and move to
the next on those errors, so a grounded answer still comes back.
"""
import structlog
from functools import lru_cache

from openai import APIStatusError, OpenAI

from app.config import settings

log = structlog.get_logger()

# Errors that mean "this model is busy/unavailable — try the next one".
_FALLBACK_STATUS = {404, 429, 502, 503}


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.openrouter_api_key or settings.openai_api_key,
        base_url=settings.openrouter_base_url or None,
    )


def models_chain() -> list[str]:
    """Ordered, de-duplicated model list: primary first, then configured fallbacks."""
    chain = [settings.generation_model] + [
        m.strip() for m in settings.generation_models.split(",") if m.strip()
    ]
    seen, out = set(), []
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _should_fallback(err: Exception) -> bool:
    return isinstance(err, APIStatusError) and err.status_code in _FALLBACK_STATUS


def chat(messages: list[dict], **kwargs) -> str:
    """Non-streaming completion. Tries each model in the chain; raises last error if all fail."""
    last: Exception | None = None
    for model in models_chain():
        try:
            resp = get_client().chat.completions.create(model=model, messages=messages, **kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001 — decide fallback by status
            last = e
            if _should_fallback(e):
                log.warning("llm.fallback", model=model, error=type(e).__name__)
                continue
            raise
    raise last if last else RuntimeError("no generation model available")


def stream_chat(messages: list[dict], **kwargs):
    """Streaming completion with fallback. Yields text deltas.

    Fallback only applies before the first token; once streaming starts on a
    model, an error there ends the stream (can't restart mid-answer).
    """
    last: Exception | None = None
    for model in models_chain():
        started = False
        try:
            stream = get_client().chat.completions.create(
                model=model, messages=messages, stream=True, **kwargs
            )
            for event in stream:
                delta = event.choices[0].delta.content
                if delta:
                    started = True
                    yield delta
            return
        except Exception as e:  # noqa: BLE001
            last = e
            if not started and _should_fallback(e):
                log.warning("llm.stream_fallback", model=model, error=type(e).__name__)
                continue
            raise
    raise last if last else RuntimeError("no generation model available")
