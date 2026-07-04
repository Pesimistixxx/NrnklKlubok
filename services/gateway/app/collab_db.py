"""Postgres: пользователи и чат команды."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from mkg_core.graph_meta import compact_message_meta
from mkg_core.meta_db import init_schema, pool

_COLLAB_INITIALIZED = False
_DEFAULT_THREAD_TITLE = "Новый чат"
_PLACEHOLDER_TITLE_RE = re.compile(r"^Чат \d+$")

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

CREATE TABLE IF NOT EXISTS role_prompts (
  role_id TEXT PRIMARY KEY,
  system_prompt TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _is_placeholder_title(title: str | None) -> bool:
    t = (title or "").strip()
    return not t or t == _DEFAULT_THREAD_TITLE or bool(_PLACEHOLDER_TITLE_RE.match(t))


def derive_thread_title(body: str, *, max_len: int = 55) -> str:
    text = re.sub(r"\s+", " ", (body or "").strip())
    if not text:
        return _DEFAULT_THREAD_TITLE
    if len(text) <= max_len:
        return text[:200]
    cut = text[:max_len].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return (cut + "…")[:200]


async def _migrate_thread_titles(conn) -> None:
    rows = await conn.fetch(
        """
        SELECT t.id,
          (SELECT body FROM chat_messages m
           WHERE m.thread_id = t.id AND m.msg_type = 'user'
           ORDER BY m.created_at ASC LIMIT 1) AS first_body
        FROM chat_threads t
        WHERE t.title = $1 OR t.title ~ '^Чат [0-9]+$'
        """,
        _DEFAULT_THREAD_TITLE,
    )
    for row in rows:
        body = row.get("first_body")
        if not body:
            continue
        title = derive_thread_title(str(body))
        await conn.execute(
            "UPDATE chat_threads SET title = $1 WHERE id = $2",
            title,
            row["id"],
        )


async def init_collab_schema() -> None:
    global _COLLAB_INITIALIZED
    if _COLLAB_INITIALIZED:
        return
    await init_schema()
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(_COLLAB_SQL)
        await _migrate_thread_titles(conn)
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


async def collab_activity_stats() -> dict[str, Any]:
    """Aggregate chat activity for manager dashboard."""
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        thread_count = int(await conn.fetchval("SELECT COUNT(*) FROM chat_threads") or 0)
        message_count = int(await conn.fetchval("SELECT COUNT(*) FROM chat_messages") or 0)
        queries_7d = int(
            await conn.fetchval(
                "SELECT COUNT(*) FROM chat_messages WHERE created_at >= now() - interval '7 days'"
            )
            or 0
        )
        recent_threads = await conn.fetch(
            """
            SELECT t.id, t.title,
              (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) AS message_count,
              (SELECT MAX(created_at) FROM chat_messages m WHERE m.thread_id = t.id) AS last_message_at
            FROM chat_threads t
            ORDER BY COALESCE(
              (SELECT MAX(created_at) FROM chat_messages m WHERE m.thread_id = t.id),
              t.created_at
            ) DESC
            LIMIT 5
            """
        )
    return {
        "thread_count": thread_count,
        "message_count": message_count,
        "queries_7d": queries_7d,
        "recent_threads": [dict(r) for r in recent_threads],
    }


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


async def get_thread(thread_id: str) -> dict[str, Any] | None:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.*,
              (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) AS message_count,
              (SELECT MAX(created_at) FROM chat_messages m WHERE m.thread_id = t.id) AS last_message_at
            FROM chat_threads t
            WHERE t.id = $1
            """,
            thread_id,
        )
    return dict(row) if row else None


async def create_thread(title: str, *, kind: str = "team", created_by: str | None = None) -> dict[str, Any]:
    await init_collab_schema()
    tid = f"thread:{uuid.uuid4().hex[:12]}"
    clean_title = title.strip()[:200] or _DEFAULT_THREAD_TITLE
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_threads (id, title, kind, created_by) VALUES ($1, $2, $3, $4)",
            tid,
            clean_title,
            kind,
            created_by,
        )
        row = await conn.fetchrow("SELECT * FROM chat_threads WHERE id = $1", tid)
    return dict(row) if row else {"id": tid, "title": clean_title, "kind": kind}


async def update_thread_title(thread_id: str, title: str) -> dict[str, Any] | None:
    await init_collab_schema()
    clean_title = title.strip()[:200] or _DEFAULT_THREAD_TITLE
    p = await pool()
    async with p.acquire() as conn:
        result = await conn.execute(
            "UPDATE chat_threads SET title = $1 WHERE id = $2",
            clean_title,
            thread_id,
        )
        if not result.endswith("1"):
            return None
    return await get_thread(thread_id)


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
    meta_json = json.dumps(compact_message_meta(meta), ensure_ascii=False)
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
        if msg_type == "user":
            thread_row = await conn.fetchrow(
                "SELECT title FROM chat_threads WHERE id = $1",
                thread_id,
            )
            if thread_row and _is_placeholder_title(str(thread_row["title"])):
                await conn.execute(
                    "UPDATE chat_threads SET title = $1 WHERE id = $2",
                    derive_thread_title(body),
                    thread_id,
                )
        row = await conn.fetchrow("SELECT * FROM chat_messages WHERE id = $1", mid)
    item = dict(row) if row else {}
    if item.get("meta") and isinstance(item["meta"], str):
        item["meta"] = json.loads(item["meta"])
    return item


async def get_message(message_id: str, thread_id: str) -> dict[str, Any] | None:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM chat_messages WHERE id = $1 AND thread_id = $2",
            message_id,
            thread_id,
        )
    if not row:
        return None
    item = dict(row)
    if item.get("meta") and isinstance(item["meta"], str):
        try:
            item["meta"] = json.loads(item["meta"])
        except json.JSONDecodeError:
            pass
    return item


async def delete_message(message_id: str, thread_id: str) -> bool:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM chat_messages WHERE id = $1 AND thread_id = $2",
            message_id,
            thread_id,
        )
    return result.endswith("1")


async def delete_messages_from(
    message_id: str,
    thread_id: str,
    *,
    inclusive: bool = True,
) -> int:
    """Удалить сообщение и все последующие в треде (по created_at)."""
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        anchor = await conn.fetchrow(
            "SELECT created_at FROM chat_messages WHERE id = $1 AND thread_id = $2",
            message_id,
            thread_id,
        )
        if not anchor:
            return 0
        op = ">=" if inclusive else ">"
        result = await conn.execute(
            f"DELETE FROM chat_messages WHERE thread_id = $1 AND created_at {op} $2",
            thread_id,
            anchor["created_at"],
        )
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0


async def update_message_body(
    message_id: str,
    thread_id: str,
    body: str,
) -> dict[str, Any] | None:
    await init_collab_schema()
    clean = body.strip()
    if not clean:
        raise ValueError("empty_body")
    p = await pool()
    async with p.acquire() as conn:
        result = await conn.execute(
            "UPDATE chat_messages SET body = $1 WHERE id = $2 AND thread_id = $3",
            clean,
            message_id,
            thread_id,
        )
        if not result.endswith("1"):
            return None
        row = await conn.fetchrow(
            "SELECT * FROM chat_messages WHERE id = $1 AND thread_id = $2",
            message_id,
            thread_id,
        )
    if not row:
        return None
    item = dict(row)
    if item.get("meta") and isinstance(item["meta"], str):
        try:
            item["meta"] = json.loads(item["meta"])
        except json.JSONDecodeError:
            pass
    return item


async def delete_thread(thread_id: str) -> bool:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        result = await conn.execute("DELETE FROM chat_threads WHERE id = $1", thread_id)
    return result.endswith("1")


async def get_role_prompt(role_id: str) -> str | None:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT system_prompt FROM role_prompts WHERE role_id = $1", role_id)
    return str(row["system_prompt"]) if row else None


async def set_role_prompt(role_id: str, system_prompt: str) -> None:
    await init_collab_schema()
    text = system_prompt.strip()
    if not text:
        raise ValueError("empty_prompt")
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO role_prompts (role_id, system_prompt, updated_at)
            VALUES ($1, $2, now())
            ON CONFLICT (role_id) DO UPDATE SET
              system_prompt = EXCLUDED.system_prompt,
              updated_at = now()
            """,
            role_id,
            text[:12000],
        )


async def delete_role_prompt(role_id: str) -> None:
    await init_collab_schema()
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM role_prompts WHERE role_id = $1", role_id)
