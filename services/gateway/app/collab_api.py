"""Collab API: 8 ролей, чат (dual Qdrant L3+L4 + graph traversal), POST /query.

Эндпоинты: /roles, /users/session, /chat/*, POST /api/v1/query (dialog | agent modes).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.chat_engine import run_chat_query
from app.collab_db import (
    add_message,
    create_thread,
    delete_message,
    delete_messages_from,
    delete_role_prompt,
    delete_thread,
    get_message,
    get_role_prompt,
    init_collab_schema,
    list_messages,
    list_threads,
    list_users,
    set_role_prompt,
    update_message_body,
    update_thread_title,
    upsert_user,
)
from app.role_prompts import default_prompt
from app.roles import MKG_ROLES, get_role
from app.schemas import (
    ChatCompleteIn,
    ChatCompleteOut,
    ChatMessageOut,
    ChatMessagesOut,
    ChatThreadCreate,
    ChatThreadOut,
    ChatThreadUpdate,
    ChatThreadsOut,
    MessageCreate,
    MessageUpdate,
    QueryTestIn,
    QueryTestOut,
    RoleOut,
    RolePromptOut,
    RolePromptUpdate,
    RolesOut,
    UserOut,
    UserSessionIn,
)

router = APIRouter(tags=["collab"])


@router.get("/roles", response_model=RolesOut)
async def get_roles() -> RolesOut:
    return RolesOut(roles=[RoleOut(**r) for r in MKG_ROLES])


@router.get("/roles/{role_id}/prompt", response_model=RolePromptOut)
async def get_role_prompt_api(role_id: str) -> RolePromptOut:
    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Неизвестная роль")
    custom = await get_role_prompt(role_id)
    default = default_prompt(role_id)
    return RolePromptOut(
        role_id=role_id,
        name_ru=str(role["name_ru"]),
        system_prompt=custom if custom else default,
        default_prompt=default,
        is_custom=custom is not None,
    )


@router.put("/roles/{role_id}/prompt", response_model=RolePromptOut)
async def put_role_prompt(role_id: str, body: RolePromptUpdate) -> RolePromptOut:
    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Неизвестная роль")
    try:
        await set_role_prompt(role_id, body.system_prompt)
    except ValueError as exc:
        if str(exc) == "empty_prompt":
            raise HTTPException(status_code=400, detail="Промпт не может быть пустым") from exc
        raise
    return await get_role_prompt_api(role_id)


@router.delete("/roles/{role_id}/prompt", response_model=RolePromptOut)
async def reset_role_prompt(role_id: str) -> RolePromptOut:
    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Неизвестная роль")
    await delete_role_prompt(role_id)
    return await get_role_prompt_api(role_id)


@router.post("/users/session", response_model=UserOut)
async def start_session(body: UserSessionIn) -> UserOut:
    role = get_role(body.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    display_name = (body.display_name or "").strip() or str(role["name_ru"])
    await init_collab_schema()
    rec = await upsert_user(display_name, body.role_id, body.user_id)
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
    title = (body.title or "").strip() or "Новый чат"
    rec = await create_thread(title, kind=body.kind, created_by=body.created_by)
    return ChatThreadOut(
        id=rec["id"],
        title=rec["title"],
        kind=rec.get("kind") or "team",
        created_by=rec.get("created_by"),
        created_at=rec.get("created_at"),
        message_count=0,
    )


def _thread_out(rec: dict[str, Any]) -> ChatThreadOut:
    return ChatThreadOut(
        id=rec["id"],
        title=rec["title"],
        kind=rec.get("kind") or "team",
        created_by=rec.get("created_by"),
        created_at=rec.get("created_at"),
        message_count=int(rec.get("message_count") or 0),
        last_message_at=rec.get("last_message_at"),
    )


@router.patch("/chat/threads/{thread_id}", response_model=ChatThreadOut)
async def patch_thread(thread_id: str, body: ChatThreadUpdate) -> ChatThreadOut:
    rec = await update_thread_title(thread_id, body.title)
    if not rec:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return _thread_out(rec)


@router.delete("/chat/threads/{thread_id}")
async def remove_thread(thread_id: str) -> dict[str, bool]:
    ok = await delete_thread(thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {"ok": True}


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


def _message_out(rec: dict[str, Any]) -> ChatMessageOut:
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


@router.delete("/chat/threads/{thread_id}/messages/{message_id}")
async def remove_thread_message(
    thread_id: str,
    message_id: str,
    cascade: str | None = None,
) -> dict[str, Any]:
    msg = await get_message(message_id, thread_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    if cascade == "following":
        deleted = await delete_messages_from(message_id, thread_id, inclusive=True)
        return {"ok": True, "deleted": deleted}
    if cascade == "after":
        deleted = await delete_messages_from(message_id, thread_id, inclusive=False)
        return {"ok": True, "deleted": deleted}
    ok = await delete_message(message_id, thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    return {"ok": True, "deleted": 1}


@router.patch("/chat/threads/{thread_id}/messages/{message_id}", response_model=ChatMessageOut)
async def patch_thread_message(
    thread_id: str,
    message_id: str,
    body: MessageUpdate,
) -> ChatMessageOut:
    msg = await get_message(message_id, thread_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    try:
        rec = await update_message_body(message_id, thread_id, body.body)
    except ValueError as exc:
        if str(exc) == "empty_body":
            raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым") from exc
        raise
    if not rec:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    return _message_out(rec)


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


@router.post("/chat/complete", response_model=ChatCompleteOut)
async def chat_complete(body: ChatCompleteIn) -> ChatCompleteOut:
    history = [{"role": t.role, "content": t.content} for t in body.history]
    return await run_chat_query(
        body.message,
        body.role_id,
        history=history,
        system_prompt=body.system_prompt,
        include_graph=body.include_graph,
        include_artifacts=body.include_artifacts,
        document_ids=body.document_ids or None,
        speed_mode=body.speed_mode,
    )


@router.post("/query", response_model=QueryTestOut, summary="Тестовый API для сложных вопросов")
async def query_test(body: QueryTestIn) -> QueryTestOut:
    """
    Программный запрос к MKG AI без чата.

    Пример:
    curl -X POST http://localhost:8000/api/v1/query \\
      -H "Content-Type: application/json" \\
      -d '{"question":"Какие материалы в документе?","role_id":"analyst","include_graph":true}'
    """
    history = [{"role": t.role, "content": t.content} for t in body.history]
    mode = body.mode or "dialog"

    if mode and mode != "dialog":
        from app.agents_proxy import proxy_agents_run

        try:
            result = await proxy_agents_run(
                query=body.question,
                mode=mode,
                doc_ids=[],
                user_role=body.role_id,
                limit=5,
                history=history,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return QueryTestOut(
            answer=result.get("summary") or "",
            trace=result.get("trace") or [],
            graph=None,
            artifacts=[],
            timing_ms=int(result.get("elapsed_ms") or 0),
            mode=mode,
        )

    out = await run_chat_query(
        body.question,
        body.role_id,
        history=history,
        system_prompt=body.system_prompt,
        include_graph=body.include_graph,
        include_artifacts=body.include_artifacts,
    )
    return QueryTestOut(
        answer=out.reply,
        trace=out.trace,
        graph=out.graph,
        artifacts=out.artifacts,
        timing_ms=out.timing_ms,
        mode="dialog",
    )
