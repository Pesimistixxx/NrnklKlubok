"""Извлечение статистики токенов из ответов LLM API."""
from __future__ import annotations

from typing import Any


def extract_llm_usage(resp: Any) -> dict[str, int | bool | None]:
    """input / output / total / cached_tokens из Responses API (OpenAI SDK)."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "cached_tokens": None,
        }

    if hasattr(usage, "model_dump"):
        data: dict[str, Any] = usage.model_dump()
    elif isinstance(usage, dict):
        data = usage
    else:
        data = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    cached = None
    details = data.get("input_tokens_details") or data.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = details.get("cached_tokens")
    if cached is None:
        cached = data.get("cached_tokens")

    return {
        "input_tokens": _int_or_none(data.get("input_tokens")),
        "output_tokens": _int_or_none(data.get("output_tokens")),
        "total_tokens": _int_or_none(data.get("total_tokens")),
        "cached_tokens": _int_or_none(cached),
    }


def cache_hit_usage() -> dict[str, int | bool | None]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "cache_hit": True,
    }


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
