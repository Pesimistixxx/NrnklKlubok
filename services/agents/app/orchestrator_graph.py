"""LangGraph оркестратор: plan → flexible agent loop (JSON bus) → discover → synthesize."""
from __future__ import annotations

import asyncio
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from mkg_core.answer_structure import SYNTH_STRUCTURE_RULES, extract_synthesis_entities
from mkg_core.query_facets import QueryFacets, enrich_search_with_facets, parse_facets_from_plan
from mkg_core.graph_meta import enrich_graph_for_persistence
from mkg_core.text_sanitize import sanitize_user_facing_text

from app.agent_bus import (
    ALL_LAYERS,
    agent_id_to_layer,
    bus_summary,
    get_pending_requests,
    layer_to_agent_id,
    make_message,
    publish,
)
from app.client import GatewayClient
from app.config import AgentSettings
from app.layer_nodes import make_layer_runner
from app.llm import AgentLLM
from app.state import OrchestratorState
from app.graph_snapshot import graph_snapshot_from_acc, snapshot_for_trace
from app.utils import (
    add_trace,
    add_warning,
    effective_search_query,
    format_history_context,
    history_memory_meta,
    normalize_list,
    prior_turns,
    remaining_seconds,
)

_LAYER_AGENTS = tuple(layer_to_agent_id(l) for l in ALL_LAYERS)
RouterTarget = Literal[
    "l1_agent", "l2_agent", "l3_agent", "l4_agent", "l5_agent", "l6_agent",
    "discover_new_connections", "orchestrator_synthesize",
]

_ORCHESTRATOR_PLAN_PROMPT = """
Ты Orchestrator Agent для knowledge graph MKG (6 слоёв L1–L6).
По вопросу пользователя выбери, какие слои обязательно исследовать.
Во входе есть conversation_history — предыдущие реплики чата.
Если текущий query короткий или это продолжение («Подумай еще раз», «уточни», «продолжи»),
keywords и focus бери из предыдущего вопроса пользователя в conversation_history, а не из текущей реплики.
Верни только JSON:
{
  "layers": ["L1","L2","L3","L4","L5","L6"],
  "focus": "кратко на русском",
  "keywords": ["..."],
  "must_find_connections": true,
  "priority_layers": ["L3","L4"],
  "query_facets": {
    "materials": ["..."],
    "processes": ["..."],
    "geography": ["domestic|foreign|страна"],
    "year_min": 2015,
    "year_max": 2024,
    "numeric_min": null,
    "numeric_max": null,
    "numeric_param": "concentration|temperature|flow_rate",
    "conditions": ["температура", "давление"]
  }
}
layers — подмножество из L1,L2,L3,L4,L5,L6. priority_layers — с чего начать (не обязательно L1).
query_facets — структурированный разбор вопроса: материал, процесс, география (domestic=RU, foreign), годы, числовые ограничения.
Декомпозируй сложный вопрос: L1=материалы/процессы, L2=география/авторы, L3=текст, L4=измерения/факты, L5=верификация, L6=ТЭП.
must_find_connections всегда true.
""".strip()

_ROUTER_PROMPT = """
Ты Orchestrator Router. Выбери следующий узел для исследования графа MKG.
Доступные агенты: l1_agent…l6_agent, discover_new_connections (завершить цикл), orchestrator_synthesize (только если данных достаточно).
Учитывай agent_bus (запросы между агентами), round/max_rounds, planned_layers, layer_results, conversation_history.
Верни только JSON: {"next": "l3_agent"|"discover_new_connections", "reason": "кратко"}
""".strip()

_GAP_PROMPT = """
Ты Connection Gap Analyzer. По подграфу MKG определи, каких связей не хватает для ответа.
Верни только JSON:
{
  "missing_connections": ["описание пробела 1", "..."],
  "expand_layers": ["L3"],
  "confidence": 0.0
}
""".strip()

_SYNTH_PROMPT = (
    """
Ты Synthesizer Agent. Сформируй структурированный ответ на русском по вопросу и evidence из слоёв L1–L6.
Во входе conversation_history — предыдущий обмен. Если query — продолжение («Подумай еще раз», «уточни»),
ответ должен явно опираться на предыдущую тему и дополнять/уточнять prior answer, а не начинать с нуля.
Верни только JSON:
{
  "summary": "Markdown с разделами ## для пользователя",
  "warnings": []
}
"""
    + SYNTH_STRUCTURE_RULES
    + """
Опирайся только на переданные узлы, layer_results, sources, knowledge_gaps, experts, anomalies и gaps.
Если данных мало — укажи в warnings и в «Пробелы в знаниях».
Никогда не включай в summary document_id, neo4j_node_id, node_id, коды L1–L6 и внутренний жаргон.
Ссылайся на документы по смыслу или названию.
"""
).strip()

# Complementary layers when a layer finds few nodes
_LAYER_GAP_TARGETS: dict[str, str] = {
    "L1": "L3",
    "L2": "L3",
    "L3": "L4",
    "L4": "L3",
    "L5": "L4",
    "L6": "L1",
}


def _layer_node_counts(state: OrchestratorState) -> dict[str, int]:
    counts = {l: 0 for l in ALL_LAYERS}
    for lr in state.get("layer_results") or []:
        layer = str(lr.get("layer") or "").upper()
        if layer in counts:
            counts[layer] += len(lr.get("nodes_found") or [])
    return counts


def _pick_next_layer_heuristic(state: OrchestratorState) -> str | None:
    """Flexible scheduling: bus requests first, then gaps, then uninvoked planned layers."""
    bus = state.get("agent_bus") or []
    round_num = int(state.get("round") or 0)
    planned = [str(x).upper() for x in (state.get("planned_layers") or list(ALL_LAYERS))]
    planned_set = {l for l in planned if l in ALL_LAYERS}
    invoked = {str(x).upper() for x in (state.get("layers_invoked") or [])}

    pending = get_pending_requests(bus, round_num=round_num)
    for msg in pending:
        msg_type = str(msg.get("type") or "")
        if msg_type == "anomaly_found":
            to = str(msg.get("to") or "")
            if to.endswith("_agent"):
                layer = agent_id_to_layer(to)
                if layer in planned_set:
                    return layer
            payload = msg.get("payload") or {}
            target = str(payload.get("target_layer") or "L3").upper()
            if target in planned_set:
                return target
        to = str(msg.get("to") or "")
        if to.endswith("_agent"):
            layer = agent_id_to_layer(to)
            if layer in planned_set:
                return layer
        payload = msg.get("payload") or {}
        layer = str(payload.get("layer") or payload.get("target_layer") or "").upper()
        if layer in planned_set:
            return layer

    counts = _layer_node_counts(state)
    priority = state.get("orchestrator_plan") or {}
    prio_list = [str(x).upper() for x in (priority.get("priority_layers") or []) if str(x).upper() in planned_set]

    remaining = [l for l in planned if l not in invoked]
    if not remaining and round_num + 1 < int(state.get("max_rounds") or 1):
        weak = [l for l in planned if counts.get(l, 0) < 2]
        if weak:
            return weak[0]

    if remaining:
        for layer in prio_list:
            if layer in remaining:
                return layer
        weak_first = sorted(remaining, key=lambda l: counts.get(l, 0))
        return weak_first[0]

    return None


def _resolve_router_target(state: OrchestratorState, settings: AgentSettings) -> RouterTarget:
    round_num = int(state.get("round") or 0)
    max_rounds = int(state.get("max_rounds") or settings.agent_loop_max_rounds)

    if remaining_seconds(state, settings.timeout_seconds) < 2.0:
        return "discover_new_connections"

    next_layer = _pick_next_layer_heuristic(state)
    if next_layer:
        return layer_to_agent_id(next_layer)  # type: ignore[return-value]

    if round_num + 1 < max_rounds:
        counts = _layer_node_counts(state)
        planned = [str(x).upper() for x in (state.get("planned_layers") or list(ALL_LAYERS))]
        if any(counts.get(l, 0) < 2 for l in planned):
            return layer_to_agent_id(planned[0])  # type: ignore[return-value]

    return "discover_new_connections"


async def orchestrator_init(
    state: OrchestratorState,
    gateway: GatewayClient,
    settings: AgentSettings,
) -> OrchestratorState:
    new_state = dict(state)
    doc_ids = list(new_state.get("doc_ids") or [])
    if doc_ids:
        new_state["candidate_doc_ids"] = doc_ids[: settings.max_docs]
    else:
        try:
            payload = await gateway.docs(page_size=settings.max_docs)
            docs = [d for d in payload.get("items", []) if d.get("status") == "loaded"][: settings.max_docs]
            new_state["candidate_doc_ids"] = [d["id"] for d in docs if d.get("id")]
        except Exception as exc:
            add_warning(new_state, f"документы недоступны: {exc}")
            new_state["candidate_doc_ids"] = []
    new_state.setdefault("accumulated_graph", {"nodes": [], "relationships": [], "document_ids": [], "new_connections": []})
    new_state.setdefault("layer_results", [])
    new_state.setdefault("planned_layers", list(ALL_LAYERS))
    new_state.setdefault("agent_bus", [])
    new_state.setdefault("round", 0)
    new_state.setdefault("max_rounds", settings.agent_loop_max_rounds)
    new_state.setdefault("layers_invoked", [])
    history = list(new_state.get("history") or [])
    memory = history_memory_meta(history)
    add_trace(
        new_state,
        "orchestrator_init",
        doc_count=len(new_state.get("candidate_doc_ids") or []),
        history_turn_count=memory["turn_count"],
        history_truncated=memory["truncated"],
    )
    if memory["turn_count"]:
        add_trace(
            new_state,
            "chat_memory",
            turn_count=memory["turn_count"],
            truncated=memory["truncated"],
        )
    return new_state


async def orchestrator_plan(
    state: OrchestratorState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> OrchestratorState:
    new_state = dict(state)
    new_state["round"] = 0
    new_state["max_rounds"] = settings.agent_loop_max_rounds
    new_state["agent_bus"] = []
    new_state["layers_invoked"] = []

    timeout = min(settings.planner_timeout * 2, remaining_seconds(new_state, settings.timeout_seconds))
    if timeout <= 0:
        new_state["planned_layers"] = list(ALL_LAYERS)
        add_trace(new_state, "orchestrator_plan", source="fallback_timeout", layers=new_state["planned_layers"])
        _trace_loop_start(new_state)
        return new_state
    try:
        prior_user, prior_assistant = prior_turns(new_state.get("history") or [])
        plan = await llm.generate_json(
            instructions=_ORCHESTRATOR_PLAN_PROMPT,
            payload={
                "query": new_state.get("query"),
                "doc_count": len(new_state.get("candidate_doc_ids") or []),
                "conversation_history": format_history_context(new_state.get("history") or []),
                "prior_user_question": prior_user,
                "prior_assistant_summary": prior_assistant,
            },
            max_tokens=350,
            timeout=timeout,
        )
    except Exception as exc:
        add_warning(new_state, f"orchestrator plan fallback: {exc}")
        plan = {}
    layers = plan.get("layers") if isinstance(plan, dict) else None
    valid = set(ALL_LAYERS)
    if isinstance(layers, list):
        picked = [str(x).upper() for x in layers if str(x).upper() in valid]
    else:
        picked = []
    if not picked:
        picked = list(ALL_LAYERS)
    new_state["planned_layers"] = picked
    new_state["orchestrator_plan"] = plan if isinstance(plan, dict) else {"layers": picked}
    facets = parse_facets_from_plan(plan if isinstance(plan, dict) else {})
    new_state["query_facets"] = facets.to_dict()
    bus = list(new_state.get("agent_bus") or [])
    if facets.to_dict():
        bus = publish(
            bus,
            make_message(
                from_agent="orchestrator",
                to="broadcast",
                type_="query_facets",
                payload={
                    "query_facets": facets.to_dict(),
                    "focus": plan.get("focus") if isinstance(plan, dict) else None,
                    "layers": picked,
                    "search_hint": enrich_search_with_facets(
                        str(new_state.get("query") or ""),
                        facets,
                    ),
                },
                round_num=0,
            ),
        )
        new_state["agent_bus"] = bus
    add_trace(
        new_state,
        "orchestrator_plan",
        layers=picked,
        focus=(plan.get("focus") if isinstance(plan, dict) else None),
        priority_layers=(plan.get("priority_layers") if isinstance(plan, dict) else None),
        query_facets=new_state.get("query_facets"),
        history_turn_count=history_memory_meta(new_state.get("history") or []).get("turn_count", 0),
    )
    _trace_loop_start(new_state)
    return new_state


def _trace_loop_start(state: OrchestratorState) -> None:
    add_trace(
        state,
        "agent_loop_start",
        round=state.get("round", 0),
        max_rounds=state.get("max_rounds"),
        planned_layers=state.get("planned_layers"),
        loop_phase="flexible_bus",
    )
    add_trace(
        state,
        "layer_loop_start",
        round=state.get("round", 0),
        max_rounds=state.get("max_rounds"),
        planned_layers=state.get("planned_layers"),
        loop_phase="flexible_bus",
        loop_total=len(state.get("planned_layers") or []),
    )


async def orchestrator_router(
    state: OrchestratorState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> OrchestratorState:
    """Decide next agent or exit loop; stores orchestrator_next for conditional edge."""
    new_state = dict(state)
    target = _resolve_router_target(new_state, settings)

    timeout = min(settings.planner_timeout, remaining_seconds(new_state, settings.timeout_seconds))
    if timeout > 0.5 and target in _LAYER_AGENTS:
        try:
            routed = await llm.generate_json(
                instructions=_ROUTER_PROMPT,
                payload={
                    "query": new_state.get("query"),
                    "conversation_history": format_history_context(new_state.get("history") or []),
                    "round": new_state.get("round"),
                    "max_rounds": new_state.get("max_rounds"),
                    "planned_layers": new_state.get("planned_layers"),
                    "layers_invoked": new_state.get("layers_invoked"),
                    "pending_bus": get_pending_requests(new_state.get("agent_bus") or []),
                    "layer_counts": _layer_node_counts(new_state),
                    "heuristic_next": target,
                },
                max_tokens=120,
                timeout=timeout,
            )
            if isinstance(routed, dict):
                nxt = str(routed.get("next") or "").lower()
                if nxt in _LAYER_AGENTS or nxt in ("discover_new_connections", "orchestrator_synthesize"):
                    target = nxt  # type: ignore[assignment]
        except Exception:
            pass

    new_state["orchestrator_next"] = target
    add_trace(
        new_state,
        "orchestrator_router",
        round=new_state.get("round"),
        max_rounds=new_state.get("max_rounds"),
        next_agent=target,
        bus_size=len(new_state.get("agent_bus") or []),
        bus_preview=bus_summary(new_state.get("agent_bus")),
        layers_invoked=list(new_state.get("layers_invoked") or []),
    )
    return new_state


def _router_edge(state: OrchestratorState) -> str:
    nxt = str(state.get("orchestrator_next") or "discover_new_connections")
    if nxt in _LAYER_AGENTS or nxt in ("discover_new_connections", "connection_gap_analyzer", "orchestrator_synthesize"):
        return nxt
    return "discover_new_connections"


async def orchestrator_advance_round(state: OrchestratorState, settings: AgentSettings) -> OrchestratorState:
    """After a layer agent finishes: track invocation, maybe advance round."""
    new_state = dict(state)
    last = (new_state.get("layer_results") or [])[-1] if new_state.get("layer_results") else None
    if last:
        layer = str(last.get("layer") or "").upper()
        invoked = list(new_state.get("layers_invoked") or [])
        if layer and layer not in invoked:
            invoked.append(layer)
        new_state["layers_invoked"] = invoked

        planned = [str(x).upper() for x in (new_state.get("planned_layers") or list(ALL_LAYERS))]
        if planned and all(l in invoked for l in planned):
            round_num = int(new_state.get("round") or 0)
            max_rounds = int(new_state.get("max_rounds") or settings.agent_loop_max_rounds)
            if round_num + 1 < max_rounds:
                new_state["round"] = round_num + 1
                new_state["layers_invoked"] = []
                add_trace(
                    new_state,
                    "agent_loop_round",
                    round=new_state["round"],
                    max_rounds=max_rounds,
                    reason="all_planned_layers_invoked",
                )
    return new_state


async def discover_connections_node(
    state: OrchestratorState,
    settings: AgentSettings,
) -> OrchestratorState:
    from mkg_core.graph_traversal import discover_new_connections

    new_state = dict(state)
    acc = dict(new_state.get("accumulated_graph") or {})
    doc_ids = list(new_state.get("candidate_doc_ids") or [])
    search_q = effective_search_query(str(new_state.get("query") or ""), new_state.get("history") or [])
    try:
        expanded = await discover_new_connections(
            acc,
            search_q,
            document_ids=doc_ids or None,
            max_paths=10,
        )
    except Exception as exc:
        add_warning(new_state, f"discover_new_connections: {exc}")
        expanded = acc
    new_state["accumulated_graph"] = expanded
    counts = expanded.get("discovery_counts") or {}
    add_trace(
        new_state,
        "discover_new_connections",
        round=new_state.get("round"),
        node_count=len(expanded.get("nodes") or []),
        rel_count=len(expanded.get("relationships") or []),
        cross_layer=counts.get("cross_layer", 0),
        cross_document=counts.get("cross_document", 0),
        neo4j_paths=counts.get("neo4j_paths", 0),
        total_discoveries=counts.get("total", 0),
        graph_snapshot=snapshot_for_trace(
            expanded,
            doc_ids=list(new_state.get("candidate_doc_ids") or []),
        ),
    )
    return new_state


async def connection_gap_analyzer(
    state: OrchestratorState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> OrchestratorState:
    new_state = dict(state)
    acc = new_state.get("accumulated_graph") or {}
    timeout = min(settings.analyzer_timeout, remaining_seconds(new_state, settings.timeout_seconds))
    gap: dict[str, Any] = {}
    if timeout > 0.3:
        try:
            gap = await llm.generate_json(
                instructions=_GAP_PROMPT,
                payload={
                    "query": new_state.get("query"),
                    "conversation_history": format_history_context(new_state.get("history") or []),
                    "node_count": len(acc.get("nodes") or []),
                    "rel_count": len(acc.get("relationships") or []),
                    "layer_results": new_state.get("layer_results") or [],
                    "new_connections": (acc.get("new_connections") or [])[:12],
                    "agent_bus": bus_summary(new_state.get("agent_bus"), limit=8),
                },
                max_tokens=400,
                timeout=timeout,
            )
        except Exception as exc:
            add_warning(new_state, f"gap analyzer: {exc}")
    new_state["connection_gaps"] = gap if isinstance(gap, dict) else {}
    missing = normalize_list((gap or {}).get("missing_connections"))
    expand = gap.get("expand_layers") if isinstance(gap, dict) else []
    round_num = int(new_state.get("round") or 0)
    bus = list(new_state.get("agent_bus") or [])

    if isinstance(expand, list) and expand and remaining_seconds(new_state, settings.timeout_seconds) > 1.0:
        for layer in expand[:2]:
            layer_id = str(layer).upper()
            if layer_id in ALL_LAYERS:
                bus = publish(
                    bus,
                    make_message(
                        from_agent="connection_gap_analyzer",
                        to=layer_to_agent_id(layer_id),
                        type_="gap_found",
                        payload={
                            "layer": layer_id,
                            "gap": missing[0].get("value") if missing else "нужно больше evidence",
                            "missing_connections": [m.get("value") for m in missing[:3]],
                        },
                        round_num=round_num,
                    ),
                )
        new_state["agent_bus"] = bus
        new_state["orchestrator_next"] = layer_to_agent_id(str(expand[0]).upper())
        add_trace(
            new_state,
            "connection_gap_analyzer",
            missing_count=len(missing),
            expanded_layers=expand,
            bus_posted=True,
            next_agent=new_state["orchestrator_next"],
        )
        return new_state

    add_trace(
        new_state,
        "connection_gap_analyzer",
        missing_count=len(missing),
        expanded_layers=expand if isinstance(expand, list) else [],
    )
    new_state["orchestrator_next"] = "orchestrator_synthesize"
    return new_state


def _gap_edge(state: OrchestratorState) -> str:
    nxt = str(state.get("orchestrator_next") or "orchestrator_synthesize")
    if nxt in _LAYER_AGENTS:
        return nxt
    return "orchestrator_synthesize"


async def orchestrator_synthesize(
    state: OrchestratorState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> OrchestratorState:
    new_state = dict(state)
    acc = new_state.get("accumulated_graph") or {}
    timeout = min(settings.builder_timeout * 2, remaining_seconds(new_state, settings.timeout_seconds))
    summary = "Недостаточно данных из графа для ответа."
    warnings = list(new_state.get("warnings") or [])
    if timeout > 0.3:
        nodes_preview = []
        for n in (acc.get("nodes") or [])[:20]:
            props = n.get("props") or {}
            nodes_preview.append(
                {
                    "id": n.get("id"),
                    "label": n.get("label"),
                    "text": (props.get("name_ru") or props.get("quote") or props.get("raw_text_ru") or "")[:200],
                }
            )
        try:
            prior_user, prior_assistant = prior_turns(new_state.get("history") or [])
            synth_ctx = extract_synthesis_entities(acc)
            result = await llm.generate_json(
                instructions=_SYNTH_PROMPT,
                payload={
                    "query": new_state.get("query"),
                    "conversation_history": format_history_context(new_state.get("history") or []),
                    "prior_user_question": prior_user,
                    "prior_assistant_summary": prior_assistant,
                    "layer_results": new_state.get("layer_results") or [],
                    "sources": synth_ctx.get("source_hints") or [],
                    "knowledge_gaps": synth_ctx.get("knowledge_gaps") or [],
                    "experts": synth_ctx.get("experts") or [],
                    "anomalies": synth_ctx.get("anomalies") or [],
                    "nodes": nodes_preview,
                    "relationships": (acc.get("relationships") or [])[:24],
                    "new_connections": (acc.get("new_connections") or [])[:16],
                    "gaps": new_state.get("connection_gaps") or {},
                    "agent_bus": bus_summary(new_state.get("agent_bus"), limit=10),
                    "rounds_completed": int(new_state.get("round") or 0) + 1,
                },
                max_tokens=settings.llm_max_output_tokens,
                timeout=timeout,
            )
            if isinstance(result, dict) and result.get("summary"):
                summary = sanitize_user_facing_text(str(result["summary"]))
                for w in normalize_list(result.get("warnings")):
                    val = w.get("value") or w.get("message")
                    if val:
                        warnings.append(str(val))
        except asyncio.TimeoutError:
            warnings.append("timeout: synthesizer не успел")
        except Exception as exc:
            warnings.append(f"synthesizer: {exc}")
    elif acc.get("nodes"):
        summary = f"Найдено {len(acc.get('nodes') or [])} узлов и {len(acc.get('relationships') or [])} связей по слоям MKG."

    trace = normalize_list(new_state.get("trace"))
    graph_payload = enrich_graph_for_persistence(
        {
            "nodes": acc.get("nodes") or [],
            "relationships": acc.get("relationships") or [],
            "seed_count": len(acc.get("nodes") or []),
            "document_ids": list(acc.get("document_ids") or new_state.get("candidate_doc_ids") or []),
            "new_connections": acc.get("new_connections") or [],
        },
        trace,
        layer_results=list(new_state.get("layer_results") or []),
    )
    new_state["final_response"] = {
        "mode": "orchestrator_mode",
        "query": new_state.get("query", ""),
        "summary": summary,
        "issues": [],
        "hypotheses": [],
        "recommendations": [],
        "anomalies": [],
        "literature_review": {},
        "evidence": [],
        "graph": graph_payload,
        "trace": trace,
        "warnings": warnings,
        "orchestrator_plan": new_state.get("orchestrator_plan") or {},
        "layer_results": new_state.get("layer_results") or [],
        "agent_bus": bus_summary(new_state.get("agent_bus")),
        "round": new_state.get("round"),
        "max_rounds": new_state.get("max_rounds"),
    }
    add_trace(new_state, "orchestrator_synthesize", node_count=len(graph_payload["nodes"]), round=new_state.get("round"), graph_snapshot=snapshot_for_trace(acc, doc_ids=list(new_state.get("candidate_doc_ids") or [])))
    new_state["final_response"]["trace"] = normalize_list(new_state.get("trace"))
    return new_state


def build_orchestrator_graph(settings: AgentSettings, gateway: GatewayClient, llm: AgentLLM):
    graph = StateGraph(OrchestratorState)

    async def _init(state: OrchestratorState) -> OrchestratorState:
        return await orchestrator_init(state, gateway, settings)

    async def _plan(state: OrchestratorState) -> OrchestratorState:
        return await orchestrator_plan(state, llm, settings)

    async def _router(state: OrchestratorState) -> OrchestratorState:
        return await orchestrator_router(state, llm, settings)

    async def _discover(state: OrchestratorState) -> OrchestratorState:
        return await discover_connections_node(state, settings)

    async def _gap(state: OrchestratorState) -> OrchestratorState:
        return await connection_gap_analyzer(state, llm, settings)

    async def _synth(state: OrchestratorState) -> OrchestratorState:
        return await orchestrator_synthesize(state, llm, settings)

    graph.add_node("orchestrator_init", _init)
    graph.add_node("orchestrator_plan", _plan)
    graph.add_node("orchestrator_router", _router)

    for layer in ALL_LAYERS:
        lid = layer_to_agent_id(layer)
        runner = make_layer_runner(layer)

        async def _layer(state: OrchestratorState, *, _runner=runner, _lid=lid) -> OrchestratorState:
            result = await _runner(state, gateway, settings)
            return await orchestrator_advance_round(result, settings)

        graph.add_node(lid, _layer)

    graph.add_node("discover_new_connections", _discover)
    graph.add_node("connection_gap_analyzer", _gap)
    graph.add_node("orchestrator_synthesize", _synth)

    graph.set_entry_point("orchestrator_init")
    graph.add_edge("orchestrator_init", "orchestrator_plan")
    graph.add_edge("orchestrator_plan", "orchestrator_router")

    graph.add_conditional_edges("orchestrator_router", _router_edge)
    for lid in _LAYER_AGENTS:
        graph.add_edge(lid, "orchestrator_router")

    graph.add_edge("discover_new_connections", "connection_gap_analyzer")
    graph.add_conditional_edges("connection_gap_analyzer", _gap_edge)
    graph.add_edge("orchestrator_synthesize", END)

    return graph.compile()
