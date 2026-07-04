from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    audit = "audit_mode"
    hypothesis = "hypothesis_mode"
    literature_review = "literature_review_mode"
    recommendation = "recommendation_mode"
    anomaly = "anomaly_mode"
    orchestrator = "orchestrator_mode"


class AgentRunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    mode: AgentMode | None = None
    doc_ids: list[str] = Field(default_factory=list)
    user_role: str = "researcher"
    limit: int = Field(default=5, ge=1, le=20)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


class AgentRunOut(BaseModel):
    mode: str
    query: str
    elapsed_ms: int
    summary: str
    issues: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    literature_review: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    graph: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    layer_results: list[dict[str, Any]] | None = None
    orchestrator_plan: dict[str, Any] | None = None


class ModeInfo(BaseModel):
    id: AgentMode
    title: str
    description: str


class ModesOut(BaseModel):
    modes: list[ModeInfo]


class HealthOut(BaseModel):
    status: str
    gateway_url: str
    llm_configured: bool
    llm_model: str
