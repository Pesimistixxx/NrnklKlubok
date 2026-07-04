"""Роль текущего пользователя из заголовка / query (MVP-сессия)."""
from __future__ import annotations

from fastapi import Request

from app.roles import get_role

_ROLE_HEADER = "X-MKG-Role"


def role_from_request(
    request: Request | None,
    *,
    body_role_id: str | None = None,
    default: str = "viewer",
) -> str:
    candidates: list[str | None] = []
    if request is not None:
        candidates.append(request.headers.get(_ROLE_HEADER))
        candidates.append(request.query_params.get("role_id"))
    candidates.append(body_role_id)
    for raw in candidates:
        rid = (raw or "").strip()
        if rid and get_role(rid):
            return rid
    fallback = (default or "viewer").strip()
    return fallback if get_role(fallback) else "viewer"


def role_header_name() -> str:
    return _ROLE_HEADER
