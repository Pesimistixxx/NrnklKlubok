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
    history: list[dict[str, str]] | None = None,
    speed_mode: str = "full",
) -> dict:
    """Вызов LangGraph agents service, возвращает сырой JSON."""
    url = f"{_agents_base()}/api/v1/agents/run"
    payload: dict = {"query": query, "user_role": user_role, "limit": limit, "speed_mode": speed_mode}
    if mode:
        payload["mode"] = mode
    if doc_ids:
        payload["doc_ids"] = doc_ids
    if history:
        payload["history"] = history
    else:
        payload["history"] = []
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


async def proxy_agents_run_async(
    *,
    query: str,
    mode: str = "orchestrator_mode",
    doc_ids: list[str] | None = None,
    user_role: str = "researcher",
    limit: int = 5,
    history: list[dict[str, str]] | None = None,
) -> dict:
    """Старт async orchestrator run, возвращает {run_id, status}."""
    url = f"{_agents_base()}/api/v1/agents/run/async"
    payload: dict = {
        "query": query,
        "mode": mode,
        "user_role": user_role,
        "limit": limit,
        "speed_mode": "full",
        "history": history or [],
    }
    if doc_ids:
        payload["doc_ids"] = doc_ids
    timeout = 15.0
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


async def proxy_agents_run_status(run_id: str) -> dict:
    """Poll async orchestrator run status."""
    url = f"{_agents_base()}/api/v1/agents/run/{run_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
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
            history=[{"role": t.role, "content": t.content} for t in body.history],
            speed_mode=body.speed_mode,
        )
        return AgentServiceRunOut(**data)
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Agents service timeout") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service: {exc}") from exc


@router.post("/agents-service/run/async")
async def agents_run_async(body: AgentServiceRunIn) -> dict:
    try:
        return await proxy_agents_run_async(
            query=body.query,
            mode=body.mode or "orchestrator_mode",
            doc_ids=body.doc_ids or None,
            user_role=body.user_role,
            limit=body.limit,
            history=[{"role": t.role, "content": t.content} for t in body.history],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service: {exc}") from exc


@router.get("/agents-service/run/{run_id}")
async def agents_run_status(run_id: str) -> dict:
    try:
        return await proxy_agents_run_status(run_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service: {exc}") from exc
