"""Поисковые запросы с учётом истории чата (общий для gateway и agents)."""
from __future__ import annotations

import re

_CONTINUATION_MARKERS = (
    "подумай еще",
    "подумай ещё",
    "уточни",
    "продолжи",
    "разверни",
    "расскажи подробнее",
    "еще раз",
    "ещё раз",
    "дополни",
    "переформулируй",
    "уточни ответ",
    "поясни",
    "объясни подробнее",
    "а про",
    "а что",
    "а как",
)


def compact_text(text: str, limit: int = 420) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def prior_turns(history: list[dict[str, str]] | None) -> tuple[str, str]:
    """Последний вопрос пользователя и последний ответ ассистента (без текущего message)."""
    prior_user = ""
    prior_assistant = ""
    for turn in reversed(list(history or [])):
        role = str(turn.get("role") or "user")
        content = str(turn.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant" and not prior_assistant:
            prior_assistant = compact_text(content, 500)
        elif role == "user" and not prior_user:
            prior_user = compact_text(content, 500)
        if prior_user and prior_assistant:
            break
    return prior_user, prior_assistant


def is_continuation_query(query: str) -> bool:
    q = query.strip().lower()
    if not q:
        return False
    if any(marker in q for marker in _CONTINUATION_MARKERS):
        return True
    return len(q.split()) <= 4 and any(marker in q for marker in _CONTINUATION_MARKERS)


_TOKEN_RE = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)


def _norm_token(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_standalone_topic_query(query: str) -> bool:
    """Короткий самостоятельный запрос (материал, термин) — не смешивать с прошлым вопросом."""
    q = query.strip()
    if not q or is_continuation_query(q):
        return False
    try:
        from mkg_core.query_classify import is_conversational_query

        if is_conversational_query(q):
            return True
    except Exception:
        pass
    words = q.split()
    if len(words) > 3:
        return False
    try:
        from mkg_core.alias_expansion import get_alias_lookup

        lookup = get_alias_lookup()
        tokens = [_norm_token(t) for t in _TOKEN_RE.findall(q) if len(_norm_token(t)) >= 2]
        if any(t in lookup for t in tokens):
            return True
    except Exception:
        pass
    return len(words) <= 2


def effective_search_query(query: str, history: list[dict[str, str]] | None, *, limit: int = 600) -> str:
    """Поисковый запрос с учётом истории для коротких и продолжающих реплик."""
    q = query.strip()
    if not q:
        return q
    prior_user, prior_assistant = prior_turns(history)
    if is_standalone_topic_query(q):
        base = q
    elif is_continuation_query(q) and prior_user:
        parts = [prior_user, q]
        if prior_assistant:
            parts.append(prior_assistant[:200])
        base = compact_text(" ".join(parts), limit)
    elif len(q.split()) <= 3 and prior_user:
        base = compact_text(f"{prior_user} {q}", limit)
    else:
        base = q
    try:
        from mkg_core.alias_expansion import expand_search_query

        expanded, _added = expand_search_query(base, limit=limit)
        return expanded
    except Exception:
        return base


def search_query_variants(
    query: str,
    history: list[dict[str, str]] | None,
    *,
    limit: int = 600,
) -> list[str]:
    """Варианты запроса для retrieval: сначала расширенный, затем сырой (без истории)."""
    raw = query.strip()
    effective = effective_search_query(query, history, limit=limit)
    variants: list[str] = []
    seen: set[str] = set()
    for candidate in (effective, raw):
        key = candidate.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        variants.append(candidate.strip())
    return variants
