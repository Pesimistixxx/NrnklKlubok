"""Postgres metadata storage for documents and jobs.

Минимальная рабочая реализация на asyncpg:
- init_schema()
- upsert_document()
- update_document_status()
- get_document()
- list_documents()
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import asyncpg

from mkg_core.config import get_settings

_POOL: asyncpg.Pool | None = None
_INITIALIZED = False


async def pool() -> asyncpg.Pool:
    global _POOL
    if _POOL is None:
        _POOL = await asyncpg.create_pool(get_settings().asyncpg_dsn(), min_size=1, max_size=5)
    return _POOL


_MIGRATION_COLUMNS = (
    "source_location TEXT",
    "geography TEXT",
    "material_date DATE",
    "tags TEXT[]",
    "ingested_at TIMESTAMPTZ",
)


async def init_schema() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    sql = """
    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      doc_type TEXT,
      classification TEXT,
      organization TEXT,
      hash_sum TEXT UNIQUE NOT NULL,
      status TEXT NOT NULL,
      upload_date TIMESTAMPTZ NOT NULL,
      size_bytes BIGINT NOT NULL,
      lang TEXT,
      step TEXT,
      error TEXT,
      neo4j_synced BOOLEAN,
      graph_nodes INTEGER,
      graph_relationships INTEGER,
      source_location TEXT,
      geography TEXT,
      material_date DATE,
      tags TEXT[],
      ingested_at TIMESTAMPTZ,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(sql)
        for col_def in _MIGRATION_COLUMNS:
            await conn.execute(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {col_def}")
    _INITIALIZED = True


async def upsert_document(record: dict[str, Any]) -> None:
    await init_schema()
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (
              id, file_name, doc_type, classification, organization, hash_sum,
              status, upload_date, size_bytes, lang, step, error, neo4j_synced,
              graph_nodes, graph_relationships, source_location, geography,
              material_date, tags, ingested_at, updated_at
            )
            VALUES (
              $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,now()
            )
            ON CONFLICT (id) DO UPDATE SET
              file_name=EXCLUDED.file_name,
              doc_type=EXCLUDED.doc_type,
              classification=EXCLUDED.classification,
              organization=EXCLUDED.organization,
              hash_sum=EXCLUDED.hash_sum,
              status=EXCLUDED.status,
              upload_date=EXCLUDED.upload_date,
              size_bytes=EXCLUDED.size_bytes,
              lang=EXCLUDED.lang,
              step=EXCLUDED.step,
              error=EXCLUDED.error,
              neo4j_synced=EXCLUDED.neo4j_synced,
              graph_nodes=EXCLUDED.graph_nodes,
              graph_relationships=EXCLUDED.graph_relationships,
              source_location=EXCLUDED.source_location,
              geography=EXCLUDED.geography,
              material_date=EXCLUDED.material_date,
              tags=EXCLUDED.tags,
              ingested_at=EXCLUDED.ingested_at,
              updated_at=now()
            """,
            record.get("id"),
            record.get("file_name"),
            record.get("doc_type"),
            record.get("classification"),
            record.get("organization"),
            record.get("hash_sum"),
            record.get("status", "uploaded"),
            _to_dt(record.get("upload_date")),
            record.get("size_bytes", 0),
            record.get("lang"),
            record.get("step"),
            record.get("error"),
            record.get("neo4j_synced"),
            record.get("graph_nodes"),
            record.get("graph_relationships"),
            record.get("source_location"),
            record.get("geography"),
            _to_date(record.get("material_date")),
            _to_tags(record.get("tags")),
            _to_dt(record.get("ingested_at") or record.get("upload_date")),
        )


async def update_document_status(doc_id: str, status: str, **extra: Any) -> None:
    await init_schema()
    p = await pool()
    fields = ["status = $2", "updated_at = now()"]
    args: list[Any] = [doc_id, status]
    idx = 3
    allowed = {
        "doc_type",
        "classification",
        "organization",
        "lang",
        "step",
        "error",
        "neo4j_synced",
        "graph_nodes",
        "graph_relationships",
        "source_location",
        "geography",
        "material_date",
        "tags",
        "ingested_at",
    }
    for k, v in extra.items():
        if k in allowed:
            fields.append(f"{k} = ${idx}")
            args.append(v)
            idx += 1
    query = f"UPDATE documents SET {', '.join(fields)} WHERE id = $1"
    async with p.acquire() as conn:
        await conn.execute(query, *args)


async def get_document(doc_id: str) -> dict[str, Any] | None:
    await init_schema()
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", doc_id)
        return _row_to_dict(row) if row else None


async def list_documents(
    page: int = 1,
    page_size: int = 20,
    *,
    geography: str | None = None,
    material_year: int | None = None,
    classifications: list[str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    await init_schema()
    p = await pool()
    offset = (page - 1) * page_size
    where: list[str] = []
    args: list[Any] = []
    idx = 1
    if geography:
        where.append(f"geography = ${idx}")
        args.append(geography)
        idx += 1
    if material_year is not None:
        where.append(f"EXTRACT(YEAR FROM material_date) = ${idx}")
        args.append(material_year)
        idx += 1
    if classifications:
        where.append(f"COALESCE(classification, 'открытый') = ANY(${idx})")
        args.append(list(classifications))
        idx += 1
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    async with p.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM documents{where_sql}", *args)
        rows = await conn.fetch(
            f"""
            SELECT * FROM documents
            {where_sql}
            ORDER BY upload_date DESC
            OFFSET ${idx} LIMIT ${idx + 1}
            """,
            *args,
            offset,
            page_size,
        )
    return [_row_to_dict(r) for r in rows], int(total or 0)


async def count_restricted_documents(
    *,
    geography: str | None = None,
    material_year: int | None = None,
    allowed_classifications: list[str] | None = None,
) -> int:
    if not allowed_classifications:
        return 0
    await init_schema()
    p = await pool()
    where: list[str] = ["COALESCE(classification, 'открытый') != ALL($1)"]
    args: list[Any] = [list(allowed_classifications)]
    idx = 2
    if geography:
        where.append(f"geography = ${idx}")
        args.append(geography)
        idx += 1
    if material_year is not None:
        where.append(f"EXTRACT(YEAR FROM material_date) = ${idx}")
        args.append(material_year)
        idx += 1
    where_sql = f" WHERE {' AND '.join(where)}"
    async with p.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM documents{where_sql}", *args)
    return int(total or 0)


async def delete_document(doc_id: str) -> bool:
    await init_schema()
    p = await pool()
    async with p.acquire() as conn:
        result = await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
    try:
        return int(str(result).split()[-1]) > 0
    except Exception:
        return False


async def clear_all_documents() -> int:
    await init_schema()
    p = await pool()
    async with p.acquire() as conn:
        result = await conn.execute("DELETE FROM documents")
    try:
        count = int(str(result).split()[-1])
    except Exception:
        count = 0
    return count


def _to_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _to_date(value: Any):
    from datetime import date as date_cls

    if value is None:
        return None
    if isinstance(value, date_cls):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        try:
            return date_cls.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _to_tags(value: Any) -> list[str] | None:
    if not value:
        return None
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value if x]
    return [str(value)]


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    mat = data.get("material_date")
    if mat is not None and hasattr(mat, "isoformat"):
        data["material_date"] = mat.isoformat()
    tags = data.get("tags")
    if tags is not None:
        data["tags"] = list(tags)
    ing = data.get("ingested_at")
    if isinstance(ing, datetime):
        data["ingested_at"] = ing.isoformat()
    up = data.get("upload_date")
    if isinstance(up, datetime):
        data["upload_date"] = up.isoformat()
    upd = data.get("updated_at")
    if isinstance(upd, datetime):
        data["updated_at"] = upd.isoformat()
    return data
