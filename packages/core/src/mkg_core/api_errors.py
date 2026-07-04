"""Критичные ошибки API — пайплайн должен останавливаться."""
from __future__ import annotations


def is_fatal_api_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    markers = (
        "401",
        "403",
        "unauthenticated",
        "unauthorized",
        "api key not found",
        "api key",
        "invalid api",
        "permission denied",
        "quota",
        "billing",
    )
    return any(m in msg for m in markers)


def format_api_error(exc: BaseException, *, model: str | None = None) -> str:
    model_part = f"Модель: {model}. " if model else ""
    return f"{model_part}{exc}"
