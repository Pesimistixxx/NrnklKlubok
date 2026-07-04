"""API пользователей, ролей и командного чата."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from mkg_core.config import get_settings
from mkg_core.llm import YandexLLMClient

from app.collab_db import (
    add_message,
    create_thread,
    delete_role_prompt,
    delete_thread,
    get_role_prompt,
    init_collab_schema,
    list_messages,
    list_threads,
    list_users,
    set_role_prompt,
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
    ChatThreadsOut,
    MessageCreate,
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
    rec = await create_thread(body.title, kind=body.kind, created_by=body.created_by)
    return ChatThreadOut(
        id=rec["id"],
        title=rec["title"],
        kind=rec.get("kind") or "team",
        created_by=rec.get("created_by"),
        created_at=rec.get("created_at"),
        message_count=0,
    )


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
    role = get_role(body.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        raise HTTPException(
            status_code=503,
            detail="LLM не настроен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID",
        )
    custom = await get_role_prompt(body.role_id)
    system = (body.system_prompt or custom or default_prompt(body.role_id)).strip()
    lines: list[str] = []
    for turn in body.history[-12:]:
        label = "Пользователь" if turn.role == "user" else "Ассистент"
        lines.append(f"{label}: {turn.content.strip()}")
    lines.append(f"Пользователь: {body.message.strip()}")
    user_prompt = "\n\n".join(lines)
    try:
        llm = YandexLLMClient.instance()
        reply = await llm.chat(
            system,
            user_prompt,
            temperature=0.35,
            max_tokens=1536,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {exc}") from exc
    text = (reply or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="LLM вернул пустой ответ")
    return ChatCompleteOut(reply=text)
