"""Роли пользователей MKG — связь с агентами ТЗ и agents service user_role."""
from __future__ import annotations

from typing import Any

MKG_ROLES: list[dict[str, Any]] = [
    {
        "id": "admin",
        "name_ru": "Администратор",
        "agent_id": "security",
        "agents_user_role": "admin",
        "can_upload": True,
        "can_extract": True,
        "can_admin": True,
        "can_run_agents": True,
        "description": "Полный доступ, настройки, очистка базы",
    },
    {
        "id": "researcher",
        "name_ru": "Исследователь",
        "agent_id": "synthesis",
        "agents_user_role": "researcher",
        "can_upload": True,
        "can_extract": True,
        "can_admin": False,
        "can_run_agents": True,
        "description": "Гипотезы, обзоры литературы, рекомендации",
    },
    {
        "id": "engineer",
        "name_ru": "Инженер данных",
        "agent_id": "ingestion",
        "agents_user_role": "engineer",
        "can_upload": True,
        "can_extract": True,
        "can_admin": False,
        "can_run_agents": False,
        "description": "OCR, ingestion, extraction, Neo4j",
    },
    {
        "id": "analyst",
        "name_ru": "Аналитик",
        "agent_id": "retrieval",
        "agents_user_role": "analyst",
        "can_upload": False,
        "can_extract": False,
        "can_admin": False,
        "can_run_agents": True,
        "description": "Граф, Qdrant, семантический поиск",
    },
    {
        "id": "validator",
        "name_ru": "Валидатор",
        "agent_id": "validation",
        "agents_user_role": "validator",
        "can_upload": False,
        "can_extract": False,
        "can_admin": False,
        "can_run_agents": True,
        "description": "Audit mode — противоречия и качество фактов",
    },
    {
        "id": "security",
        "name_ru": "Безопасность",
        "agent_id": "security",
        "agents_user_role": "security",
        "can_upload": False,
        "can_extract": False,
        "can_admin": False,
        "can_run_agents": False,
        "description": "RBAC, грифы, SecurityRole L5",
    },
    {
        "id": "viewer",
        "name_ru": "Наблюдатель",
        "agent_id": "notification",
        "agents_user_role": "viewer",
        "can_upload": False,
        "can_extract": False,
        "can_admin": False,
        "can_run_agents": False,
        "description": "Только просмотр документов и графа",
    },
]

_ROLES_BY_ID = {r["id"]: r for r in MKG_ROLES}


def get_role(role_id: str) -> dict[str, Any] | None:
    return _ROLES_BY_ID.get(role_id)


def agents_user_role(role_id: str) -> str:
    role = get_role(role_id)
    return str(role["agents_user_role"]) if role else "researcher"
