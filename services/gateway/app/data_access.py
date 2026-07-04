"""Классификация документов и матрица доступа role × classification."""
from __future__ import annotations

import json
from typing import Any

from app.roles import MKG_ROLES, get_role

CLASSIFICATION_LEVELS: tuple[str, ...] = (
    "открытый",
    "внутренний",
    "конфиденциальный",
    "строго",
)

_CONFIG_KEY = "data_access_matrix"

_DEFAULT_MATRIX: dict[str, list[str]] = {
    "admin": list(CLASSIFICATION_LEVELS),
    "viewer": ["открытый"],
    "researcher": ["открытый", "внутренний"],
    "analyst": ["открытый", "внутренний"],
    "engineer": ["открытый", "внутренний"],
    "validator": ["открытый", "внутренний"],
    "security": list(CLASSIFICATION_LEVELS),
}

_MATRIX_CACHE: dict[str, list[str]] | None = None


def role_ids() -> list[str]:
    return [str(r["id"]) for r in MKG_ROLES if str(r["id"]) != "admin"]


def normalize_classification(value: str | None) -> str:
    raw = (value or "открытый").strip().lower()
    if raw in CLASSIFICATION_LEVELS:
        return raw
    aliases = {
        "public": "открытый",
        "open": "открытый",
        "internal": "внутренний",
        "confidential": "конфиденциальный",
        "restricted": "строго",
        "strict": "строго",
    }
    return aliases.get(raw, "открытый")


def default_matrix() -> dict[str, list[str]]:
    return {rid: list(levels) for rid, levels in _DEFAULT_MATRIX.items()}


async def _ensure_schema() -> None:
    from mkg_core.runtime_config import init_runtime_schema

    await init_runtime_schema()


async def load_data_access_matrix(*, force: bool = False) -> dict[str, list[str]]:
    global _MATRIX_CACHE
    if _MATRIX_CACHE is not None and not force:
        return dict(_MATRIX_CACHE)
    merged = default_matrix()
    try:
        await _ensure_schema()
        from mkg_core.meta_db import pool

        p = await pool()
        async with p.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM runtime_config WHERE key = $1",
                _CONFIG_KEY,
            )
        if row and row["value"]:
            stored = json.loads(str(row["value"]))
            if isinstance(stored, dict):
                for role_id, levels in stored.items():
                    if role_id == "admin":
                        continue
                    if role_id not in merged:
                        continue
                    if isinstance(levels, list):
                        merged[role_id] = [
                            normalize_classification(x)
                            for x in levels
                            if normalize_classification(x) in CLASSIFICATION_LEVELS
                        ]
    except Exception:
        pass
    merged["admin"] = list(CLASSIFICATION_LEVELS)
    _MATRIX_CACHE = merged
    return dict(merged)


async def save_data_access_matrix(updates: dict[str, list[str]]) -> dict[str, list[str]]:
    global _MATRIX_CACHE
    current = await load_data_access_matrix(force=True)
    for role_id, levels in updates.items():
        if role_id == "admin" or role_id not in current:
            continue
        current[role_id] = sorted(
            {
                normalize_classification(x)
                for x in levels
                if normalize_classification(x) in CLASSIFICATION_LEVELS
            },
            key=lambda c: CLASSIFICATION_LEVELS.index(c),
        )
    current["admin"] = list(CLASSIFICATION_LEVELS)
    await _ensure_schema()
    from mkg_core.meta_db import pool

    payload = {k: v for k, v in current.items() if k != "admin"}
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO runtime_config (key, value, updated_at)
            VALUES ($1, $2, now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            """,
            _CONFIG_KEY,
            json.dumps(payload, ensure_ascii=False),
        )
    _MATRIX_CACHE = current
    return dict(current)


def matrix_to_checkboxes(matrix: dict[str, list[str]]) -> dict[str, dict[str, bool]]:
    out: dict[str, dict[str, bool]] = {}
    for role in MKG_ROLES:
        rid = str(role["id"])
        allowed = set(matrix.get(rid) or [])
        if rid == "admin":
            allowed = set(CLASSIFICATION_LEVELS)
        out[rid] = {level: level in allowed for level in CLASSIFICATION_LEVELS}
    return out


def checkboxes_to_matrix(checkboxes: dict[str, dict[str, bool]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for rid, cols in checkboxes.items():
        if rid == "admin":
            out[rid] = list(CLASSIFICATION_LEVELS)
            continue
        out[rid] = [
            level
            for level in CLASSIFICATION_LEVELS
            if cols.get(level)
        ]
    return out


async def allowed_classifications(role_id: str) -> list[str]:
    if role_id == "admin":
        return list(CLASSIFICATION_LEVELS)
    role = get_role(role_id)
    if not role:
        return ["открытый"]
    matrix = await load_data_access_matrix()
    levels = matrix.get(role_id)
    if levels:
        return list(levels)
    embedded = role.get("allowed_classifications")
    if isinstance(embedded, list) and embedded:
        return [normalize_classification(x) for x in embedded]
    return ["открытый"]


def can_access_classification(
    classification: str | None,
    allowed: list[str],
) -> bool:
    return normalize_classification(classification) in set(allowed)


async def public_data_access_config() -> dict[str, Any]:
    matrix = await load_data_access_matrix()
    return {
        "classifications": list(CLASSIFICATION_LEVELS),
        "roles": [str(r["id"]) for r in MKG_ROLES],
        "role_names": {str(r["id"]): str(r["name_ru"]) for r in MKG_ROLES},
        "matrix": matrix_to_checkboxes(matrix),
        "defaults": default_matrix(),
    }


async def filter_records_by_access(
    records: list[dict[str, Any]],
    allowed: list[str],
) -> tuple[list[dict[str, Any]], int]:
    visible: list[dict[str, Any]] = []
    hidden = 0
    for rec in records:
        cls = normalize_classification(rec.get("classification"))
        if can_access_classification(cls, allowed):
            visible.append(rec)
        else:
            hidden += 1
    return visible, hidden


async def assert_document_access(role_id: str, classification: str | None) -> None:
    from fastapi import HTTPException

    allowed = await allowed_classifications(role_id)
    if not can_access_classification(classification, allowed):
        raise HTTPException(status_code=403, detail="Недостаточно прав для доступа к документу")


def filter_hits_by_classifications(
    hits: list[dict[str, Any]],
    allowed: list[str],
    class_map: dict[str, str],
) -> list[dict[str, Any]]:
    allowed_set = set(allowed)
    out: list[dict[str, Any]] = []
    for hit in hits:
        doc_id = str(hit.get("document_id") or "")
        if not doc_id:
            out.append(hit)
            continue
        cls = normalize_classification(class_map.get(doc_id))
        if cls in allowed_set:
            out.append(hit)
    return out


async def classification_map_for_hits(hits: list[dict[str, Any]]) -> dict[str, str]:
    doc_ids = sorted({str(h.get("document_id") or "") for h in hits if h.get("document_id")})
    if not doc_ids:
        return {}
    out: dict[str, str] = {}
    try:
        from mkg_core import get_document as db_get_document
    except ImportError:
        db_get_document = None  # type: ignore[assignment]
    from app.storage import get_repo

    repo = get_repo()
    for doc_id in doc_ids:
        rec = None
        if db_get_document:
            try:
                rec = await db_get_document(doc_id)
            except Exception:
                rec = None
        if not rec:
            rec = repo.get(doc_id)
        out[doc_id] = normalize_classification((rec or {}).get("classification"))
    return out
