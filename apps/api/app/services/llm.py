"""LLM client factory — OpenRouter (OpenAI-compatible) by default.

OpenRouter exposes an OpenAI-compatible /chat/completions endpoint, so the
OpenAI SDK works unchanged by pointing base_url at it. Free models use the
":free" suffix (e.g. meta-llama/llama-3.3-70b-instruct:free).

Used for both text generation and multimodal (vision) parsing.
"""
from functools import lru_cache

from openai import OpenAI

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """OpenAI SDK client pointed at OpenRouter (or plain OpenAI if no base_url)."""
    return OpenAI(
        api_key=settings.openrouter_api_key or settings.openai_api_key,
        base_url=settings.openrouter_base_url or None,
    )


def chat(messages: list[dict], model: str | None = None, **kwargs) -> str:
    """Single-shot chat completion -> assistant text."""
    resp = get_client().chat.completions.create(
        model=model or settings.generation_model,
        messages=messages,
        **kwargs,
    )
    return resp.choices[0].message.content or ""
