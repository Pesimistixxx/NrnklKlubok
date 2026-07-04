from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.client import GatewayClient
from app.config import AgentSettings
from app.llm import AgentLLM
from app.nodes import (
    agent_loop_controller,
    capabilities_check,
    choose_loop,
    choose_mode,
    consensus_detector,
    document_selector,
    evidence_collector,
    expert_finder,
    final_report_builder,
    graph_context_loader,
    literature_grouper,
    llm_evidence_analyzer,
    llm_mode_builder,
    llm_scope_planner,
    pattern_discovery,
    ranking_agent,
    retrieval_search,
    route_by_mode,
    technology_coverage_analyzer,
)
from app.state import MKGAgentState


def _after_planner(state: MKGAgentState) -> str:
    return "final_report_builder" if state.get("fatal_error") else "document_selector"


def _after_analyzer(state: MKGAgentState) -> str:
    return "final_report_builder" if state.get("fatal_error") else "agent_loop_controller"


def build_agent_graph(settings: AgentSettings, gateway: GatewayClient, llm: AgentLLM):
    graph = StateGraph(MKGAgentState)

    async def _capabilities_check(state: MKGAgentState) -> MKGAgentState:
        return await capabilities_check(state, gateway)

    async def _llm_scope_planner(state: MKGAgentState) -> MKGAgentState:
        return await llm_scope_planner(state, llm, settings)

    async def _document_selector(state: MKGAgentState) -> MKGAgentState:
        return await document_selector(state, gateway, settings)

    async def _retrieval_search(state: MKGAgentState) -> MKGAgentState:
        return await retrieval_search(state, gateway, settings)

    async def _graph_context_loader(state: MKGAgentState) -> MKGAgentState:
        return await graph_context_loader(state, gateway, settings)

    async def _llm_evidence_analyzer(state: MKGAgentState) -> MKGAgentState:
        return await llm_evidence_analyzer(state, llm, settings)

    async def _agent_loop_controller(state: MKGAgentState) -> MKGAgentState:
        return await agent_loop_controller(state, settings)

    async def _llm_mode_builder(state: MKGAgentState) -> MKGAgentState:
        return await llm_mode_builder(state, llm, settings)

    graph.add_node("capabilities_check", _capabilities_check)
    graph.add_node("llm_scope_planner", _llm_scope_planner)
    graph.add_node("document_selector", _document_selector)
    graph.add_node("retrieval_search", _retrieval_search)
    graph.add_node("graph_context_loader", _graph_context_loader)
    graph.add_node("evidence_collector", evidence_collector)
    graph.add_node("llm_evidence_analyzer", _llm_evidence_analyzer)
    graph.add_node("agent_loop_controller", _agent_loop_controller)
    graph.add_node("literature_grouper", literature_grouper)
    graph.add_node("technology_coverage_analyzer", technology_coverage_analyzer)
    graph.add_node("consensus_detector", consensus_detector)
    graph.add_node("route_by_mode", route_by_mode)
    graph.add_node("pattern_discovery", pattern_discovery)
    graph.add_node("audit_mode_builder", _llm_mode_builder)
    graph.add_node("hypothesis_mode_builder", _llm_mode_builder)
    graph.add_node("literature_review_mode_builder", _llm_mode_builder)
    graph.add_node("recommendation_mode_builder", _llm_mode_builder)
    graph.add_node("expert_finder", expert_finder)
    graph.add_node("ranking_agent", ranking_agent)
    graph.add_node("final_report_builder", final_report_builder)

    graph.set_entry_point("capabilities_check")
    graph.add_edge("capabilities_check", "llm_scope_planner")
    graph.add_conditional_edges(
        "llm_scope_planner",
        _after_planner,
        {
            "document_selector": "document_selector",
            "final_report_builder": "final_report_builder",
        },
    )
    graph.add_edge("document_selector", "retrieval_search")
    graph.add_edge("retrieval_search", "graph_context_loader")
    graph.add_edge("graph_context_loader", "evidence_collector")
    graph.add_edge("evidence_collector", "llm_evidence_analyzer")
    graph.add_conditional_edges(
        "llm_evidence_analyzer",
        _after_analyzer,
        {
            "agent_loop_controller": "agent_loop_controller",
            "final_report_builder": "final_report_builder",
        },
    )
    graph.add_conditional_edges(
        "agent_loop_controller",
        choose_loop,
        {
            "retry": "retrieval_search",
            "continue": "literature_grouper",
        },
    )
    graph.add_edge("literature_grouper", "technology_coverage_analyzer")
    graph.add_edge("technology_coverage_analyzer", "consensus_detector")
    graph.add_edge("consensus_detector", "route_by_mode")
    graph.add_conditional_edges(
        "route_by_mode",
        choose_mode,
        {
            "audit_mode": "audit_mode_builder",
            "hypothesis_mode": "pattern_discovery",
            "literature_review_mode": "literature_review_mode_builder",
            "recommendation_mode": "recommendation_mode_builder",
        },
    )
    graph.add_edge("pattern_discovery", "hypothesis_mode_builder")
    graph.add_edge("audit_mode_builder", "final_report_builder")
    graph.add_edge("hypothesis_mode_builder", "expert_finder")
    graph.add_edge("literature_review_mode_builder", "final_report_builder")
    graph.add_edge("recommendation_mode_builder", "expert_finder")
    graph.add_edge("expert_finder", "ranking_agent")
    graph.add_edge("ranking_agent", "final_report_builder")
    graph.add_edge("final_report_builder", END)

    return graph.compile()
