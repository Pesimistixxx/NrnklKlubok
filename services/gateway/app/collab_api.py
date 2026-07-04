"""API пользователей, ролей и командного чата."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.collab_db import (
    add_message,
    create_thread,
    init_collab_schema,
    list_messages,
    list_threads,
    list_users,
    upsert_user,
)
from app.roles import MKG_ROLES, get_role
from app.schemas import (
    ChatMessageOut,
    ChatMessagesOut,
    ChatThreadCreate,
    ChatThreadOut,
    ChatThreadsOut,
    MessageCreate,
    RoleOut,
    RolesOut,
    UserOut,
    UserSessionIn,
)

router = APIRouter(tags=["collab"])


@router.get("/roles", response_model=RolesOut)
async def get_roles() -> RolesOut:
    return RolesOut(roles=[RoleOut(**r) for r in MKG_ROLES])


@router.post("/users/session", response_model=UserOut)
async def start_session(body: UserSessionIn) -> UserOut:
    if not get_role(body.role_id):
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    await init_collab_schema()
    rec = await upsert_user(body.display_name, body.role_id, body.user_id)
    return UserOut(
        id=rec["id"],
        display_name=rec["display_name"],
        role_id=rec["role_id"],
        created_at=rec.get("created_at"),
        last_seen_at=rec.get("last_seen_at"),
    )


@router.get("/users", response_model=list[UserOut])
async def get_users() -> list[UserOut]:
    rows = await list_users()
    return [
        UserOut(
            id=r["id"],
            display_name=r["display_name"],
            role_id=r["role_id"],
            created_at=r.get("created_at"),
            last_seen_at=r.get("last_seen_at"),
        )
        for r in rows
    ]


@router.get("/chat/threads", response_model=ChatThreadsOut)
async def get_threads() -> ChatThreadsOut:
    rows = await list_threads()
    items = [
        ChatThreadOut(
            id=r["id"],
            title=r["title"],
            kind=r.get("kind") or "team",
            created_by=r.get("created_by"),
            created_at=r.get("created_at"),
            message_count=int(r.get("message_count") or 0),
            last_message_at=r.get("last_message_at"),
        )
        for r in rows
    ]
    return ChatThreadsOut(items=items, total=len(items))


@router.post("/chat/threads", response_model=ChatThreadOut)
async def post_thread(body: ChatThreadCreate) -> ChatThreadOut:
    rec = await create_thread(body.title, kind=body.kind, created_by=body.created_by)
    return ChatThreadOut(
        id=rec["id"],
        title=rec["title"],
        kind=rec.get("kind") or "team",
        created_by=rec.get("created_by"),
        created_at=rec.get("created_at"),
        message_count=0,
    )


@router.get("/chat/threads/{thread_id}/messages", response_model=ChatMessagesOut)
async def get_thread_messages(thread_id: str, limit: int = 200) -> ChatMessagesOut:
    rows = await list_messages(thread_id, limit=limit)
    items = [
        ChatMessageOut(
            id=r["id"],
            thread_id=r["thread_id"],
            author_id=r.get("author_id"),
            author_name=r["author_name"],
            author_role=r["author_role"],
            body=r["body"],
            msg_type=r.get("msg_type") or "user",
            meta=r.get("meta") or {},
            created_at=r.get("created_at"),
        )
        for r in rows
    ]
    return ChatMessagesOut(thread_id=thread_id, items=items, total=len(items))


@router.post("/chat/threads/{thread_id}/messages", response_model=ChatMessageOut)
async def post_thread_message(thread_id: str, body: MessageCreate) -> ChatMessageOut:
    if not get_role(body.author_role):
        raise HTTPException(status_code=400, detail="Неизвестная роль автора")
    try:
        rec = await add_message(
            thread_id,
            author_id=body.author_id,
            author_name=body.author_name,
            author_role=body.author_role,
            body=body.body,
            msg_type=body.msg_type,
            meta=body.meta,
        )
    except ValueError as exc:
        if str(exc) == "thread_not_found":
            raise HTTPException(status_code=404, detail="Чат не найден") from exc
        raise
    return ChatMessageOut(
        id=rec["id"],
        thread_id=rec["thread_id"],
        author_id=rec.get("author_id"),
        author_name=rec["author_name"],
        author_role=rec["author_role"],
        body=rec["body"],
        msg_type=rec.get("msg_type") or "user",
        meta=rec.get("meta") or {},
        created_at=rec.get("created_at"),
    )
