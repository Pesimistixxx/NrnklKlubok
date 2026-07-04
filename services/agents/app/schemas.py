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


class AgentRunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    mode: AgentMode | None = None
    doc_ids: list[str] = Field(default_factory=list)
    user_role: str = "researcher"
    limit: int = Field(default=5, ge=1, le=20)


class AgentRunOut(BaseModel):
    mode: AgentMode
    query: str
    elapsed_ms: int
    summary: str
    issues: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    literature_review: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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
