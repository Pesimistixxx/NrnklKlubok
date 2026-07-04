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
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(sql)
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
              graph_nodes, graph_relationships, updated_at
            )
            VALUES (
              $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,now()
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
        return dict(row) if row else None


async def list_documents(page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
    await init_schema()
    p = await pool()
    offset = (page - 1) * page_size
    async with p.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM documents")
        rows = await conn.fetch(
            """
            SELECT * FROM documents
            ORDER BY upload_date DESC
            OFFSET $1 LIMIT $2
            """,
            offset,
            page_size,
        )
    return [dict(r) for r in rows], int(total or 0)


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
