from __future__ import annotations

from typing import Any, Literal, TypedDict


AgentModeLiteral = Literal[
    "audit_mode",
    "hypothesis_mode",
    "literature_review_mode",
    "recommendation_mode",
    "anomaly_mode",
    "orchestrator_mode",
]


class MKGAgentState(TypedDict, total=False):
    start_ts: float
    query: str
    mode: AgentModeLiteral
    requested_mode: AgentModeLiteral | None
    doc_ids: list[str]
    user_role: str
    limit: int
    retry_count: int
    loop_decision: Literal["retry", "continue"]
    hypothesis_refinement_count: int
    hypothesis_refinement_decision: Literal["refine", "continue"]
    current_search_query: str | None
    used_search_queries: list[str]
    builder_feedback: str | None
    warnings: list[str]
    trace: list[dict[str, Any]]
    fatal_error: str | None
    timed_out_node: str | None

    capabilities: dict[str, Any]
    scope: dict[str, Any]
    candidate_doc_ids: list[str]
    docs: list[dict[str, Any]]
    search_hits: list[dict[str, Any]]
    node_context: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    source_groups: list[dict[str, Any]]
    technology_coverage: dict[str, Any]
    consensus_points: list[dict[str, Any]]
    disagreement_zones: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    related_experts: list[dict[str, Any]]
    related_labs: list[dict[str, Any]]
    analysis: dict[str, Any]
    mode_result: dict[str, Any]
    anomaly_seeds: list[dict[str, Any]]
    walk_graph: dict[str, Any]
    final_response: dict[str, Any]


class OrchestratorState(TypedDict, total=False):
    start_ts: float
    query: str
    doc_ids: list[str]
    user_role: str
    limit: int
    warnings: list[str]
    trace: list[dict[str, Any]]
    fatal_error: str | None

    candidate_doc_ids: list[str]
    planned_layers: list[str]
    orchestrator_plan: dict[str, Any]
    layer_results: list[dict[str, Any]]
    accumulated_graph: dict[str, Any]
    connection_gaps: dict[str, Any]
    final_response: dict[str, Any]

    # Flexible agent loop + JSON bus
    agent_bus: list[dict[str, Any]]
    round: int
    max_rounds: int
    layers_invoked: list[str]
    orchestrator_next: str | None
