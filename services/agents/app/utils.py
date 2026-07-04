from __future__ import annotations

import re
import time
from typing import Any

from app.state import MKGAgentState


def elapsed_ms(state: MKGAgentState) -> int:
    return int((time.perf_counter() - float(state.get("start_ts", time.perf_counter()))) * 1000)


def remaining_seconds(state: MKGAgentState, total: float, reserve: float = 0.15) -> float:
    elapsed = elapsed_ms(state) / 1000
    return max(0.0, total - elapsed - reserve)


def add_warning(state: MKGAgentState, message: str) -> None:
    warnings = state.setdefault("warnings", [])
    if message not in warnings:
        warnings.append(message)


def add_trace(state: MKGAgentState, step: str, **data: Any) -> None:
    trace = state.setdefault("trace", [])
    trace.append({"step": step, "elapsed_ms": elapsed_ms(state), **data})


def text_from_props(props: dict[str, Any]) -> str:
    for key in ("raw_text_ru", "quote", "text", "name_ru", "title_ru", "value", "name", "title"):
        value = props.get(key)
        if isinstance(value, str) and value.strip():
            return re.sub(r"\s+", " ", value.strip())
    return ""


def compact_text(text: str, limit: int = 420) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def format_history_context(history: list[dict[str, str]] | None, *, limit: int = 12) -> str:
    """Форматировать историю чата для LLM-контекста."""
    turns = list(history or [])[-limit:]
    if len(turns) > 10:
        turns = turns[:2] + turns[-8:]
    lines: list[str] = []
    if len(history or []) > 10:
        lines.append("(Ранние реплики сокращены.)")
    for turn in turns:
        role = turn.get("role") or "user"
        label = "Пользователь" if role == "user" else "Ассистент"
        content = str(turn.get("content") or "").strip()
        if content:
            lines.append(f"{label}: {content[:2000]}")
    return "\n".join(lines)


def normalize_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item if isinstance(item, dict) else {"value": item} for item in value]
    return []


def normalize_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
