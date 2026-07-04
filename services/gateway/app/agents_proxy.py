"""Прокси к LangGraph agents service (порт 8010)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from mkg_core.config import get_settings
from app.schemas import AgentServiceModesOut, AgentServiceRunIn, AgentServiceRunOut

router = APIRouter(tags=["agents-service"])


def _agents_base() -> str:
    return get_settings().agents_url.rstrip("/")


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
    url = f"{_agents_base()}/api/v1/agents/run"
    payload = body.model_dump(exclude_none=True)
    timeout = get_settings().agents_timeout_seconds + 2.0
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            if r.status_code >= 400:
                detail = r.text[:500]
                try:
                    detail = r.json().get("detail", detail)
                except Exception:
                    pass
                raise HTTPException(status_code=r.status_code, detail=detail)
            return AgentServiceRunOut(**r.json())
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Agents service timeout") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agents service: {exc}") from exc
