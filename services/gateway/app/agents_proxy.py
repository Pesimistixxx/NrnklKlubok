"""Прокси к LangGraph agents service (порт 8010)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from mkg_core.config import get_settings
from app.schemas import AgentServiceModesOut, AgentServiceRunIn, AgentServiceRunOut

router = APIRouter(tags=["agents-service"])


def _agents_base() -> str:
    return get_settings().agents_url.rstrip("/")


async def proxy_agents_run(
    *,
    query: str,
    mode: str | None = None,
    doc_ids: list[str] | None = None,
    user_role: str = "researcher",
    limit: int = 5,
) -> dict:
    """Вызов LangGraph agents service, возвращает сырой JSON."""
    url = f"{_agents_base()}/api/v1/agents/run"
    payload: dict = {"query": query, "user_role": user_role, "limit": limit}
    if mode:
        payload["mode"] = mode
    if doc_ids:
        payload["doc_ids"] = doc_ids
    timeout = get_settings().agents_timeout_seconds + 2.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload)
        if r.status_code >= 400:
            detail = r.text[:500]
            try:
                detail = r.json().get("detail", detail)
            except Exception:
                pass
            raise HTTPException(status_code=r.status_code, detail=detail)
        return r.json()


@router.get("/agents-service/health")
async def agents_health() -> dict:
    url = f"{_agents_base()}/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service недоступен: {exc}") from exc


@router.get("/agents-service/modes", response_model=AgentServiceModesOut)
async def agents_modes() -> AgentServiceModesOut:
    url = f"{_agents_base()}/api/v1/agents/modes"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            return AgentServiceModesOut(**r.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service: {exc}") from exc


@router.post("/agents-service/run", response_model=AgentServiceRunOut)
async def agents_run(body: AgentServiceRunIn) -> AgentServiceRunOut:
    try:
        data = await proxy_agents_run(
            query=body.query,
            mode=body.mode,
            doc_ids=body.doc_ids or None,
            user_role=body.user_role,
            limit=body.limit,
        )
        return AgentServiceRunOut(**data)
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Agents service timeout") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service: {exc}") from exc
