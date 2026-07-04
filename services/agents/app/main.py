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
from app.schemas import AgentMode, AgentRunOut, AgentRunRequest, HealthOut, ModeInfo, ModesOut
from app.state import MKGAgentState
from app.utils import elapsed_ms

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

    start_ts = time.perf_counter()
    gateway = GatewayClient(settings.gateway_url, timeout=settings.timeout_seconds)
    llm = AgentLLM(settings.llm_model)
    initial_state: MKGAgentState = {
        "start_ts": start_ts,
        "query": body.query,
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
    try:
        graph = build_agent_graph(settings, gateway, llm)
        state: dict[str, Any] = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=settings.timeout_seconds + 0.5,
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
