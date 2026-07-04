from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.client import GatewayClient
from app.config import get_agent_settings
from app.graph import build_agent_graph
from app.llm import AgentLLM
from app.orchestrator_graph import build_orchestrator_graph
from app.schemas import (
    AgentMode,
    AgentRunOut,
    AgentRunRequest,
    AgentRunStartOut,
    AgentRunStatusOut,
    HealthOut,
    ModeInfo,
    ModesOut,
)
from app.state import MKGAgentState
from mkg_core.graph_meta import enrich_graph_for_persistence
from app.utils import elapsed_ms
from app.graph_snapshot import graph_snapshot_from_acc
from app.run_store import create_run, get_run, update_run

API = "/api/v1/agents"

app = FastAPI(
    title="MKG Agents",
    version="0.1.0",
    description="LangGraph LLM-first analytics service for MKG.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    settings = get_agent_settings()
    return HealthOut(
        status="ok",
        gateway_url=settings.gateway_url,
        llm_configured=settings.llm_configured,
        llm_model=settings.llm_model,
    )


@app.get(f"{API}/modes", response_model=ModesOut)
async def modes() -> ModesOut:
    return ModesOut(
        modes=[
            ModeInfo(
                id=AgentMode.audit,
                title="Audit mode",
                description="Поиск неточностей, противоречий, слабых источников и неполных цепочек.",
            ),
            ModeInfo(
                id=AgentMode.hypothesis,
                title="Hypothesis mode",
                description="Генерация, критика и ранжирование исследовательских гипотез.",
            ),
            ModeInfo(
                id=AgentMode.literature_review,
                title="Literature review mode",
                description="Структурированный обзор с группировкой источников, консенсусом и зонами разногласий.",
            ),
            ModeInfo(
                id=AgentMode.recommendation,
                title="Recommendation mode",
                description="Похожие кейсы, смежные решения, эксперты, команды, лаборатории и темы для изучения.",
            ),
            ModeInfo(
                id=AgentMode.anomaly,
                title="Anomaly mode",
                description="Обход L4-аномалий графа: HDBSCAN noise, соседи Neo4j, Qdrant, объяснение причин.",
            ),
            ModeInfo(
                id=AgentMode.orchestrator,
                title="Orchestrator mode",
                description="Оркестратор L1–L6: последовательные layer agents, cross-layer/cross-doc связи, синтез.",
            ),
        ]
    )


@app.post(f"{API}/run", response_model=AgentRunOut)
async def run_agents(body: AgentRunRequest) -> AgentRunOut:
    settings = get_agent_settings()
    if not settings.llm_configured:
        raise HTTPException(
            status_code=503,
            detail="YANDEX_API_KEY и YANDEX_FOLDER_ID обязательны для LLM-first agents service",
        )

    if body.speed_mode == "fast":
        raise HTTPException(
            status_code=400,
            detail="speed_mode=fast не поддерживается в agents service; используйте gateway /chat/complete",
        )

    start_ts = time.perf_counter()
    gateway = GatewayClient(settings.gateway_url, timeout=settings.timeout_seconds)
    llm = AgentLLM(settings.llm_model)
    initial_state: MKGAgentState = {
        "start_ts": start_ts,
        "query": body.query,
        "history": [{"role": t.get("role", "user"), "content": t.get("content", "")} for t in (body.history or [])],
        "requested_mode": body.mode.value if body.mode else None,
        "mode": body.mode.value if body.mode else "hypothesis_mode",
        "doc_ids": body.doc_ids,
        "user_role": body.user_role,
        "limit": body.limit,
        "retry_count": 0,
        "loop_decision": "continue",
        "hypothesis_refinement_count": 0,
        "hypothesis_refinement_decision": "continue",
        "current_search_query": None,
        "used_search_queries": [],
        "builder_feedback": None,
        "trace": [],
        "warnings": [],
    }
    is_orchestrator = body.mode == AgentMode.orchestrator if body.mode else False
    run_timeout = settings.timeout_seconds + 0.5
    if is_orchestrator:
        run_timeout = max(run_timeout, settings.timeout_seconds * 1.2)
    orch_initial: dict[str, Any] = {
        "start_ts": start_ts,
        "query": body.query,
        "history": [{"role": t.get("role", "user"), "content": t.get("content", "")} for t in (body.history or [])],
        "doc_ids": body.doc_ids,
        "user_role": body.user_role,
        "limit": body.limit,
        "trace": [],
        "warnings": [],
    }
    try:
        if is_orchestrator:
            graph = build_orchestrator_graph(settings, gateway, llm)
            state = await asyncio.wait_for(
                graph.ainvoke(orch_initial),
                timeout=run_timeout,
            )
        else:
            graph = build_agent_graph(settings, gateway, llm)
            state = await asyncio.wait_for(
                graph.ainvoke(initial_state),
                timeout=run_timeout,
            )
    except asyncio.TimeoutError:
        state = {
            **initial_state,
            "final_response": {
                "mode": initial_state["mode"],
                "query": body.query,
                "summary": "Агентный анализ остановлен по общему timeout.",
                "issues": [],
                "hypotheses": [],
                "recommendations": [],
                "anomalies": [],
                "literature_review": {},
                "evidence": [],
                "trace": initial_state["trace"],
                "warnings": ["timeout: общий лимит времени agents service превышен"],
            },
        }
    except Exception as exc:
        state = {
            **initial_state,
            "final_response": {
                "mode": initial_state["mode"],
                "query": body.query,
                "summary": "Агентный анализ не завершён из-за внутренней ошибки.",
                "issues": [],
                "hypotheses": [],
                "recommendations": [],
                "anomalies": [],
                "literature_review": {},
                "evidence": [],
                "trace": initial_state["trace"],
                "warnings": [f"agents service error: {exc}"],
            },
        }
    finally:
        await gateway.aclose()

    final_response = state.get("final_response") or {}
    final_response["elapsed_ms"] = elapsed_ms(state)
    return AgentRunOut(**final_response)


def _orch_initial(body: AgentRunRequest, start_ts: float) -> dict[str, Any]:
    return {
        "start_ts": start_ts,
        "query": body.query,
        "history": [{"role": t.get("role", "user"), "content": t.get("content", "")} for t in (body.history or [])],
        "doc_ids": body.doc_ids,
        "user_role": body.user_role,
        "limit": body.limit,
        "trace": [],
        "warnings": [],
    }


def _publish_run_progress(run_id: str, state: dict[str, Any]) -> None:
    acc = state.get("accumulated_graph") or {}
    graph_payload = graph_snapshot_from_acc(
        acc,
        doc_ids=list(state.get("candidate_doc_ids") or []),
    )
    final = state.get("final_response") or {}
    if final.get("graph"):
        graph_payload = final["graph"]
    update_run(
        run_id,
        trace=list(state.get("trace") or []),
        graph=graph_payload,
        layer_results=list(state.get("layer_results") or []),
    )


async def _execute_orchestrator_async(run_id: str, body: AgentRunRequest) -> None:
    settings = get_agent_settings()
    start_ts = time.perf_counter()
    gateway = GatewayClient(settings.gateway_url, timeout=settings.timeout_seconds)
    llm = AgentLLM(settings.llm_model)
    orch_initial = _orch_initial(body, start_ts)
    run_timeout = max(settings.timeout_seconds + 0.5, settings.timeout_seconds * 1.2)
    try:
        update_run(run_id, status="running")
        graph = build_orchestrator_graph(settings, gateway, llm)
        final_state: dict[str, Any] = orch_initial

        async def _stream() -> None:
            nonlocal final_state
            async for state in graph.astream(orch_initial, stream_mode="values"):
                final_state = state
                _publish_run_progress(run_id, final_state)

        await asyncio.wait_for(_stream(), timeout=run_timeout)

        final_response = final_state.get("final_response") or {}
        if not final_response.get("graph"):
            acc = final_state.get("accumulated_graph") or {}
            final_response["graph"] = graph_snapshot_from_acc(
                acc,
                doc_ids=list(final_state.get("candidate_doc_ids") or []),
            )
        final_response["elapsed_ms"] = elapsed_ms(final_state)
        final_response.setdefault("mode", "orchestrator_mode")
        final_response.setdefault("query", body.query)
        final_response.setdefault("trace", list(final_state.get("trace") or []))
        final_response.setdefault("layer_results", list(final_state.get("layer_results") or []))
        final_response["graph"] = enrich_graph_for_persistence(
            final_response.get("graph") or {},
            final_response.get("trace") or list(final_state.get("trace") or []),
            layer_results=final_response.get("layer_results"),
        )
        _publish_run_progress(run_id, final_state)
        update_run(run_id, status="complete", result=final_response)
    except asyncio.TimeoutError:
        update_run(
            run_id,
            status="error",
            error="timeout: общий лимит времени agents service превышен",
        )
    except Exception as exc:
        update_run(run_id, status="error", error=str(exc)[:500])
    finally:
        await gateway.aclose()


@app.post(f"{API}/run/async", response_model=AgentRunStartOut)
async def run_agents_async(body: AgentRunRequest) -> AgentRunStartOut:
    settings = get_agent_settings()
    if not settings.llm_configured:
        raise HTTPException(
            status_code=503,
            detail="YANDEX_API_KEY и YANDEX_FOLDER_ID обязательны для LLM-first agents service",
        )
    if body.speed_mode == "fast":
        raise HTTPException(status_code=400, detail="speed_mode=fast не поддерживается в async run")
    if body.mode != AgentMode.orchestrator:
        raise HTTPException(status_code=400, detail="async run поддерживает только mode=orchestrator_mode")
    run_id = create_run()
    asyncio.create_task(_execute_orchestrator_async(run_id, body))
    return AgentRunStartOut(run_id=run_id, status="pending")


@app.get(f"{API}/run/{{run_id}}", response_model=AgentRunStatusOut)
async def run_agents_status(run_id: str) -> AgentRunStatusOut:
    rec = get_run(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run_id не найден")
    result = rec.get("result")
    return AgentRunStatusOut(
        run_id=run_id,
        status=str(rec.get("status") or "pending"),
        trace=list(rec.get("trace") or []),
        graph=rec.get("graph"),
        layer_results=rec.get("layer_results"),
        result=AgentRunOut(**result) if isinstance(result, dict) and rec.get("status") == "complete" else None,
        error=rec.get("error"),
    )
