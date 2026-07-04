"""Postgres: пользователи и чат команды."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from mkg_core.meta_db import init_schema, pool

_COLLAB_INITIALIZED = False

_COLLAB_SQL = """
CREATE TABLE IF NOT EXISTS mkg_users (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_threads (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'team',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
  author_id TEXT,
  author_name TEXT NOT NULL,
  author_role TEXT NOT NULL,
  body TEXT NOT NULL,
  msg_type TEXT NOT NULL DEFAULT 'user',
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_messages_thread_idx ON chat_messages(thread_id, created_at);
"""


async def init_collab_schema() -> None:
    global _COLLAB_INITIALIZED
    if _COLLAB_INITIALIZED:
        return
    await init_schema()
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(_COLLAB_SQL)
    _COLLAB_INITIALIZED = True


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def upsert_user(display_name: str, role_id: str, user_id: str | None = None) -> dict[str, Any]:
    await init_collab_schema()
    uid = user_id or f"user:{uuid.uuid4().hex[:12]}"
    name = display_name.strip()[:120] or "Участник"
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO mkg_users (id, display_name, role_id, created_at, last_seen_at)
            VALUES ($1, $2, $3, now(), now())
            ON CONFLICT (id) DO UPDATE SET
              display_name = EXCLUDED.display_name,
              role_id = EXCLUDED.role_id,
              last_seen_at = now()
            """,
            uid,
            name,
            role_id,
        )
        row = await conn.fetchrow("SELECT * FROM mkg_users WHERE id = $1", uid)
    return dict(row) if row else {"id": uid, "display_name": name, "role_id": role_id}


async def list_users(limit: int = 50) -> list[dict[str, Any]]:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mkg_users ORDER BY last_seen_at DESC LIMIT $1",
            limit,
        )
    return [dict(r) for r in rows]


async def list_threads(limit: int = 50) -> list[dict[str, Any]]:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.*,
              (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) AS message_count,
              (SELECT MAX(created_at) FROM chat_messages m WHERE m.thread_id = t.id) AS last_message_at
            FROM chat_threads t
            ORDER BY COALESCE(
              (SELECT MAX(created_at) FROM chat_messages m WHERE m.thread_id = t.id),
              t.created_at
            ) DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


async def create_thread(title: str, *, kind: str = "team", created_by: str | None = None) -> dict[str, Any]:
    await init_collab_schema()
    tid = f"thread:{uuid.uuid4().hex[:12]}"
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_threads (id, title, kind, created_by) VALUES ($1, $2, $3, $4)",
            tid,
            title.strip()[:200] or "Новый чат",
            kind,
            created_by,
        )
        row = await conn.fetchrow("SELECT * FROM chat_threads WHERE id = $1", tid)
    return dict(row) if row else {"id": tid, "title": title, "kind": kind}


async def list_messages(thread_id: str, limit: int = 200) -> list[dict[str, Any]]:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM chat_messages
            WHERE thread_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            thread_id,
            limit,
        )
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        if item.get("meta") and isinstance(item["meta"], str):
            try:
                item["meta"] = json.loads(item["meta"])
            except json.JSONDecodeError:
                pass
        out.append(item)
    return out


async def add_message(
    thread_id: str,
    *,
    author_id: str | None,
    author_name: str,
    author_role: str,
    body: str,
    msg_type: str = "user",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await init_collab_schema()
    mid = f"msg:{uuid.uuid4().hex[:14]}"
    meta_json = json.dumps(meta or {}, ensure_ascii=False)
    p = await pool()
    async with p.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM chat_threads WHERE id = $1", thread_id)
        if not exists:
            raise ValueError("thread_not_found")
        await conn.execute(
            """
            INSERT INTO chat_messages
              (id, thread_id, author_id, author_name, author_role, body, msg_type, meta)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            """,
            mid,
            thread_id,
            author_id,
            author_name[:120],
            author_role,
            body,
            msg_type,
            meta_json,
        )
        row = await conn.fetchrow("SELECT * FROM chat_messages WHERE id = $1", mid)
    item = dict(row) if row else {}
    if item.get("meta") and isinstance(item["meta"], str):
        item["meta"] = json.loads(item["meta"])
    return item
