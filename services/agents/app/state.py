from __future__ import annotations

from typing import Any, Literal, TypedDict


AgentModeLiteral = Literal[
    "audit_mode",
    "hypothesis_mode",
    "literature_review_mode",
    "recommendation_mode",
]


class MKGAgentState(TypedDict, total=False):
    start_ts: float
    query: str
    mode: AgentModeLiteral
    requested_mode: AgentModeLiteral | None
    doc_ids: list[str]
    user_role: str
    limit: int
    warnings: list[str]
    fatal_error: str | None
    timed_out_node: str | None

    capabilities: dict[str, Any]
    scope: dict[str, Any]
    candidate_doc_ids: list[str]
    docs: list[dict[str, Any]]
    search_hits: list[dict[str, Any]]
    node_context: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    analysis: dict[str, Any]
    mode_result: dict[str, Any]
    final_response: dict[str, Any]
