"""LLM client — multi-provider (OpenAI-compatible) with a free-model fallback chain.

Model IDs use the format  "provider>model_id"  e.g. "groq>llama-3.3-70b-versatile".
No prefix defaults to "openrouter" for backward compatibility.

Adding a new provider:
  1. Add its api_key / base_url fields to config.py.
  2. Add one entry to _PROVIDER_REGISTRY in this file.
  3. Prefix models in GENERATION_MODELS with "newprovider>".

Free ":free" OpenRouter models and Groq free-tier models are frequently
rate-limited (429) or temporarily unavailable (404/502/503). We try each
(provider, model) pair in order and fall back on those errors.
"""
import structlog
from openai import APIStatusError, OpenAI

from app.config import settings

log = structlog.get_logger()

_FALLBACK_STATUS = {404, 429, 502, 503}

# -- Provider registry --------------------------------------------------------
# One entry per provider. To add a new one: extend this dict + add env vars.

def _provider_registry() -> dict[str, dict]:
    return {
        "openrouter": {
            "api_key": settings.openrouter_api_key or settings.openai_api_key,
            "base_url": settings.openrouter_base_url,
        },
        "groq": {
            "api_key": settings.groq_api_key,
            "base_url": settings.groq_base_url,
        },
    }


_clients: dict[str, OpenAI] = {}


def _client_for(provider: str) -> OpenAI:
    if provider not in _clients:
        registry = _provider_registry()
        if provider not in registry:
            raise ValueError(
                f"Unknown LLM provider {provider!r}. Add it to _provider_registry() in llm.py."
            )
        cfg = registry[provider]
        # max_retries=0: fallback chain switches providers on 429 instead of waiting.
        _clients[provider] = OpenAI(
            api_key=cfg["api_key"] or "sk-no-key",
            base_url=cfg["base_url"] or None,
            max_retries=0,
        )
    return _clients[provider]


# -- Model chain --------------------------------------------------------------

def _parse_model(s: str) -> tuple[str, str]:
    """'groq>llama-3.3-70b-versatile' → ('groq', 'llama-3.3-70b-versatile').
    No prefix → ('openrouter', s) for backward compatibility."""
    if ">" in s:
        provider, model_id = s.split(">", 1)
        return provider.strip(), model_id.strip()
    return "openrouter", s


def models_chain() -> list[tuple[str, str]]:
    """Ordered, de-duplicated list of (provider, model_id) pairs."""
    raw = [settings.generation_model] + [
        m.strip() for m in settings.generation_models.split(",") if m.strip()
    ]
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in raw:
        if m and m not in seen:
            seen.add(m)
            out.append(_parse_model(m))
    return out


def _should_fallback(err: Exception) -> bool:
    return isinstance(err, APIStatusError) and err.status_code in _FALLBACK_STATUS


# -- Public API ---------------------------------------------------------------

def chat(messages: list[dict], **kwargs) -> str:
    """Non-streaming completion. Tries each (provider, model) in chain; raises last error if all fail."""
    last: Exception | None = None
    for provider, model in models_chain():
        try:
            log.info("llm.try", provider=provider, model=model, stream=False)
            resp = _client_for(provider).chat.completions.create(
                model=model, messages=messages, **kwargs
            )
            usage = getattr(resp, "usage", None)
            log.info("llm.ok", provider=provider, model=model, tokens=getattr(usage, "total_tokens", None))
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            last = e
            if _should_fallback(e):
                log.warning("llm.fallback", provider=provider, model=model, error=type(e).__name__)
                continue
            raise
    raise last if last else RuntimeError("no generation model available")


def stream_chat(messages: list[dict], **kwargs):
    """Streaming completion with fallback. Yields text deltas.

    Fallback only applies before the first token; once streaming starts on a
    model, an error there ends the stream (can't restart mid-answer).
    """
    last: Exception | None = None
    for provider, model in models_chain():
        started = False
        try:
            log.info("llm.try", provider=provider, model=model, stream=True)
            stream = _client_for(provider).chat.completions.create(
                model=model, messages=messages, stream=True, **kwargs
            )
            for event in stream:
                delta = event.choices[0].delta.content
                if delta:
                    if not started:
                        log.info("llm.stream_start", provider=provider, model=model)
                    started = True
                    yield delta
            log.info("llm.stream_done", provider=provider, model=model)
            return
        except Exception as e:  # noqa: BLE001
            last = e
            if not started and _should_fallback(e):
                log.warning("llm.stream_fallback", provider=provider, model=model, error=type(e).__name__)
                continue
            raise
    raise last if last else RuntimeError("no generation model available")
