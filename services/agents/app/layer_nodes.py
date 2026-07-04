"""Layer agents L1–L6: обход графа MKG по слоям (не роли пользователя)."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from mkg_core.graph_traversal import discover_new_connections, walk_for_chat
from mkg_core.ontology import L1_LABELS, L2_LABELS, L3_LABELS, L4_LABELS, L5_LABELS, L6_LABELS, LABEL_LAYER
from mkg_core.query_facets import QueryFacets, enrich_search_with_facets, filter_hits_by_facets
from mkg_core.store import get_repo

from app.agent_bus import (
    REQUEST_TYPES,
    bus_summary,
    get_messages_for,
    get_pending_requests,
    layer_to_agent_id,
    make_message,
    publish,
    respond,
)
from app.client import GatewayClient
from app.config import AgentSettings
from app.state import OrchestratorState
from app.graph_snapshot import snapshot_for_trace
from app.utils import add_trace, add_warning, compact_text, effective_search_query, prior_turns, text_from_props

_LAYER_LABELS: dict[str, frozenset[str]] = {
    "L1": L1_LABELS,
    "L2": L2_LABELS,
    "L3": L3_LABELS,
    "L4": L4_LABELS,
    "L5": L5_LABELS,
    "L6": L6_LABELS,
}

_LAYER_SEARCH: dict[str, list[str]] = {
    "L1": ["L1"],
    "L2": ["L2"],
    "L3": ["L3"],
    "L4": ["L4"],
    "L5": ["L5"],
    "L6": ["L6"],
}

_LAYER_REASONING: dict[str, str] = {
    "L1": "Material/Entity: материалы, процессы, оборудование",
    "L2": "Context: документы, эксперты, организации, HeadingContext",
    "L3": "Text: Qdrant L3 + TextParagraph и соседи",
    "L4": "Facts: утверждения L4, HDBSCAN-кластеры (cluster_name/description), аномалии noise",
    "L5": "Classification: VerificationStatus, Contradiction, AuditTrail",
    "L6": "TEP: TechnologySolution, EconomicIndicator",
}

_LAYER_AGENT_QUESTIONS: dict[str, str] = {
    "L1": "Какие материалы, процессы и оборудование связаны с запросом?",
    "L2": "Кто и где упоминается в контексте документов?",
    "L3": "Какие текстовые фрагменты релевантны вопросу?",
    "L4": "Какие факты, тематические кластеры HDBSCAN и L4-аномалии (noise) связаны с темой?",
    "L5": "Как классифицированы и верифицированы найденные данные?",
    "L6": "Какие технологические и экономические показатели затронуты?",
}


def _merge_subgraph(state: OrchestratorState, layer_result: dict[str, Any]) -> dict[str, Any]:
    acc = dict(state.get("accumulated_graph") or {"nodes": [], "relationships": [], "document_ids": []})
    seen_nodes = {
        (str((n.get("props") or {}).get("_doc_id") or ""), str(n.get("id") or ""))
        for n in acc.get("nodes") or []
    }
    seen_rels: set[tuple[str, str, str, str]] = set()
    for r in acc.get("relationships") or []:
        seen_rels.add(
            (
                str((r.get("props") or {}).get("_doc_id") or ""),
                str(r.get("from") or ""),
                str(r.get("to") or ""),
                str(r.get("type") or ""),
            )
        )
    for n in layer_result.get("nodes_found") or []:
        key = (str((n.get("props") or {}).get("_doc_id") or ""), str(n.get("id") or ""))
        if key[1] and key not in seen_nodes:
            seen_nodes.add(key)
            acc.setdefault("nodes", []).append(n)
    for r in layer_result.get("edges_found") or []:
        key = (
            str((r.get("props") or {}).get("_doc_id") or ""),
            str(r.get("from") or ""),
            str(r.get("to") or ""),
            str(r.get("type") or ""),
        )
        if key not in seen_rels:
            seen_rels.add(key)
            acc.setdefault("relationships", []).append(r)
    for conn in layer_result.get("new_connections") or []:
        acc.setdefault("new_connections", []).append(conn)
    docs = set(acc.get("document_ids") or [])
    docs.update(state.get("candidate_doc_ids") or [])
    acc["document_ids"] = sorted(d for d in docs if d)
    return acc


def _nodes_from_graph_layer(
    doc_id: str,
    graph: dict[str, Any],
    layer: str,
    query: str,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    allowed = _LAYER_LABELS.get(layer, frozenset())
    q = query.strip().lower()
    tokens = [t for t in q.split() if len(t) >= 3][:4]
    hits: list[dict[str, Any]] = []
    for node in graph.get("nodes") or []:
        label = str(node.get("label") or "")
        if label not in allowed:
            continue
        props = dict(node.get("props") or {})
        text = text_from_props(props).lower()
        score = 0.45
        if tokens and any(t in text for t in tokens):
            score += 0.35
        nid = str(node.get("id") or "")
        if not nid:
            continue
        hits.append(
            {
                "doc_id": doc_id,
                "document_id": doc_id,
                "node_id": nid,
                "neo4j_node_id": nid,
                "label": label,
                "layer": layer,
                "score": score,
                "text": compact_text(text_from_props(props), 400),
                "props": props,
            }
        )
    hits.sort(key=lambda h: -float(h.get("score") or 0))
    return hits[:limit]


def _cluster_mates(graph: dict[str, Any], seed_ids: set[str]) -> list[dict[str, Any]]:
    from mkg_core.graph_traversal import _cluster_mate_ids_from_graph

    mate_ids = _cluster_mate_ids_from_graph(graph, seed_ids)
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or []}
    out: list[dict[str, Any]] = []
    for nid in mate_ids:
        node = node_by_id.get(nid)
        if not node:
            continue
        props = dict(node.get("props") or {})
        out.append(
            {
                "node_id": nid,
                "label": node.get("label"),
                "layer": "L4",
                "text": compact_text(text_from_props(props), 300),
                "props": props,
                "score": 0.62,
                "retrieval_sources": ["cluster_mate"],
            }
        )
    return out


def _l4_noise_anomalies(
    doc_id: str,
    graph: dict[str, Any],
    query: str,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """L4 noise / HDBSCAN outliers (cluster_id=-1) релевантные запросу."""
    q = query.strip().lower()
    tokens = [t for t in q.split() if len(t) >= 3][:4]
    out: list[dict[str, Any]] = []
    for node in graph.get("nodes") or []:
        label = str(node.get("label") or "")
        if label not in L4_LABELS:
            continue
        props = dict(node.get("props") or {})
        cid = props.get("cluster_id", props.get("l4_cluster"))
        is_noise = False
        try:
            is_noise = int(cid) == -1
        except (TypeError, ValueError):
            is_noise = bool(props.get("is_anomaly"))
        if not is_noise and not props.get("is_anomaly"):
            continue
        text = text_from_props(props)
        if not text:
            continue
        text_l = text.lower()
        score = 0.48
        if q and q in text_l:
            score = 0.85
        elif tokens and any(t in text_l for t in tokens):
            score = 0.72
        nid = str(node.get("id") or "")
        if not nid:
            continue
        out.append(
            {
                "doc_id": doc_id,
                "document_id": doc_id,
                "node_id": nid,
                "neo4j_node_id": nid,
                "label": label,
                "layer": "L4",
                "score": score,
                "text": compact_text(text, 300),
                "props": props,
                "cluster_id": -1,
                "is_anomaly": True,
                "retrieval_sources": ["anomaly_noise"],
            }
        )
    out.sort(key=lambda h: -float(h.get("score") or 0))
    return out[:limit]


def _anomaly_nodes_from_layer(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flagged: list[dict[str, Any]] = []
    for node in nodes:
        props = dict(node.get("props") or {})
        cid = props.get("cluster_id", props.get("l4_cluster"))
        is_noise = False
        try:
            is_noise = int(cid) == -1
        except (TypeError, ValueError):
            is_noise = bool(props.get("is_anomaly"))
        if is_noise or props.get("is_anomaly"):
            flagged.append(node)
    return flagged


_LAYER_GAP_TARGETS: dict[str, str] = {
    "L1": "L3",
    "L2": "L3",
    "L3": "L4",
    "L4": "L3",
    "L5": "L4",
    "L6": "L1",
}


def _bus_context_for_layer(state: OrchestratorState, layer: str) -> str:
    """Сжатый контекст из шины и истории чата для поискового запроса."""
    agent_id = layer_to_agent_id(layer)
    round_num = int(state.get("round") or 0)
    bus = state.get("agent_bus") or []
    parts: list[str] = []
    prior_user, prior_assistant = prior_turns(state.get("history") or [])
    if prior_user:
        parts.append(f"[prior Q]: {prior_user}")
    if prior_assistant:
        parts.append(f"[prior A]: {prior_assistant[:200]}")
    for msg in get_messages_for(bus, agent_id, round_num=round_num, types=REQUEST_TYPES):
        payload = msg.get("payload") or {}
        text = payload.get("question") or payload.get("gap") or payload.get("reason") or ""
        if text:
            parts.append(f"[{msg.get('from')}]: {text}")
    return compact_text(" ".join(parts), 400)


def _post_layer_bus_messages(
    state: OrchestratorState,
    layer: str,
    layer_result: dict[str, Any],
    *,
    loop_phase: str,
) -> list[dict[str, Any]]:
    """Публикация в шину: ответы на запросы + gap_found при слабом слое."""
    bus = list(state.get("agent_bus") or [])
    agent_id = layer_to_agent_id(layer)
    round_num = int(state.get("round") or 0)
    node_count = len(layer_result.get("nodes_found") or [])

    for req in get_pending_requests(bus, round_num=round_num):
        to = str(req.get("to") or "").lower()
        if to not in (agent_id, "broadcast"):
            continue
        payload = req.get("payload") or {}
        target_layer = str(payload.get("layer") or "").upper()
        if target_layer and target_layer != layer:
            continue
        bus = respond(
            bus,
            from_agent=agent_id,
            to=str(req.get("from") or "orchestrator"),
            request_id=str(req.get("id") or ""),
            type_="evidence",
            payload={
                "layer": layer,
                "node_count": node_count,
                "summary": layer_result.get("situation_evaluation") or layer_result.get("reasoning_step"),
                "nodes_preview": [
                    compact_text(text_from_props(n.get("props") or {}), 80)
                    for n in (layer_result.get("nodes_found") or [])[:3]
                ],
            },
            round_num=round_num,
        )

    if node_count < 2 and loop_phase != "refinement":
        target = _LAYER_GAP_TARGETS.get(layer)
        if target:
            prior_user, _ = prior_turns(state.get("history") or [])
            layer_q = _LAYER_AGENT_QUESTIONS.get(layer, "")
            if prior_user:
                layer_q = f"{prior_user}. {layer_q}"
            bus = publish(
                bus,
                make_message(
                    from_agent=agent_id,
                    to=layer_to_agent_id(target),
                    type_="request_evidence",
                    payload={
                        "layer": target,
                        "question": f"Нужно больше данных для {layer}: {layer_q}",
                        "gap": f"Слой {layer}: найдено только {node_count} узл.",
                        "prior_question": prior_user or None,
                    },
                    round_num=round_num,
                ),
            )
    elif node_count >= 3:
        bus = publish(
            bus,
            make_message(
                from_agent=agent_id,
                to="broadcast",
                type_="graph_expand",
                payload={
                    "layer": layer,
                    "node_count": node_count,
                    "summary": layer_result.get("reasoning_step"),
                },
                round_num=round_num,
            ),
        )

    if layer == "L4":
        anomaly_count = int(layer_result.get("anomaly_count") or 0)
        if anomaly_count > 0:
            bus = publish(
                bus,
                make_message(
                    from_agent=agent_id,
                    to=layer_to_agent_id("L3"),
                    type_="anomaly_found",
                    payload={
                        "layer": "L4",
                        "target_layer": "L3",
                        "anomaly_count": anomaly_count,
                        "summary": layer_result.get("anomaly_evaluation")
                        or f"L4: {anomaly_count} noise/outlier точек (cluster_id=-1)",
                        "question": _LAYER_AGENT_QUESTIONS.get("L4", ""),
                    },
                    round_num=round_num,
                ),
            )

    return bus


_LAYER_LOOP_INDEX = {f"L{i}": i for i in range(1, 7)}
LAYER_LOOP_TOTAL = 6


async def run_layer_agent(
    state: OrchestratorState,
    gateway: GatewayClient,
    settings: AgentSettings,
    layer: str,
    *,
    loop_phase: str = "flexible_bus",
) -> OrchestratorState:
    """Один layer agent: поиск + обход + merge в accumulated_graph."""
    new_state = dict(state)
    planned = list(new_state.get("planned_layers") or ["L1", "L2", "L3", "L4", "L5", "L6"])
    loop_index = _LAYER_LOOP_INDEX.get(layer, 0)
    round_num = int(new_state.get("round") or 0)
    max_rounds = int(new_state.get("max_rounds") or 1)
    if layer not in planned:
        add_trace(
            new_state,
            f"{layer.lower()}_agent",
            skipped=True,
            reason="not_in_plan",
            layer=layer,
            loop_index=loop_index,
            loop_total=LAYER_LOOP_TOTAL,
            loop_phase=loop_phase,
            round=round_num,
            max_rounds=max_rounds,
        )
        return new_state

    query = str(new_state.get("query") or "")
    history = list(new_state.get("history") or [])
    prior_user, prior_assistant = prior_turns(history)
    doc_ids = list(new_state.get("candidate_doc_ids") or [])
    bus_ctx = _bus_context_for_layer(new_state, layer)
    prior_ctx = compact_text(
        " ".join(
            str(r.get("reasoning_step") or "")
            for r in (new_state.get("layer_results") or [])
            if r.get("reasoning_step")
        ),
        600,
    )
    history_ctx = compact_text(
        " ".join(p for p in (prior_user, prior_assistant) if p),
        400,
    )
    extra = " ".join(p for p in (prior_ctx, history_ctx, bus_ctx) if p).strip()
    facets = QueryFacets.from_dict(new_state.get("query_facets"))
    search_query = effective_search_query(query, history)
    search_query = enrich_search_with_facets(search_query, facets)
    if extra and extra not in search_query:
        search_query = compact_text(f"{search_query} {extra}", 800)
    hits: list[dict[str, Any]] = []

    if layer == "L3" or layer == "L4":
        async def search_doc(doc_id: str) -> None:
            try:
                result = await gateway.search(
                    doc_id,
                    search_query,
                    min(settings.search_limit, 8),
                )
            except Exception as exc:
                add_warning(new_state, f"{layer} Qdrant {doc_id}: {exc}")
                return
            for hit in result.get("hits") or []:
                hit_layer = str(hit.get("layer") or LABEL_LAYER.get(str(hit.get("label") or ""), ""))
                if hit_layer != layer:
                    continue
                hits.append({**hit, "doc_id": doc_id, "document_id": doc_id})

        await asyncio.gather(*(search_doc(d) for d in doc_ids[: settings.max_docs]))

    repo = get_repo()
    for doc_id in doc_ids[: settings.max_docs]:
        graph = repo.read_graph(doc_id) or {}
        if graph.get("nodes"):
            hits.extend(_nodes_from_graph_layer(doc_id, graph, layer, search_query, limit=settings.search_limit))
        if layer == "L4" and graph.get("nodes"):
            seed_ids = {str(h.get("node_id")) for h in hits if h.get("doc_id") == doc_id}
            for mate in _cluster_mates(graph, seed_ids):
                mate["doc_id"] = doc_id
                mate["document_id"] = doc_id
                hits.append(mate)
            for noise in _l4_noise_anomalies(doc_id, graph, search_query, limit=6):
                hits.append(noise)

    if layer == "L4" and doc_ids:
        try:
            payload = await gateway.anomalies(document_id=doc_ids[0], limit=6)
            for item in payload.get("items") or []:
                hits.append(
                    {
                        "doc_id": doc_ids[0],
                        "document_id": doc_ids[0],
                        "node_id": item.get("node_id"),
                        "label": item.get("label"),
                        "layer": "L4",
                        "score": float(item.get("anomaly_score") or 0.7),
                        "text": compact_text(str(item.get("text") or ""), 300),
                        "retrieval_sources": ["anomaly"],
                    }
                )
        except Exception:
            pass

    merged_hits: dict[tuple[str, str], dict[str, Any]] = {}
    for hit in hits:
        key = (str(hit.get("doc_id") or hit.get("document_id") or ""), str(hit.get("node_id") or ""))
        if not key[1]:
            continue
        existing = merged_hits.get(key)
        if existing:
            existing["score"] = max(float(existing.get("score") or 0), float(hit.get("score") or 0))
        else:
            merged_hits[key] = dict(hit)
    walk_hits = list(merged_hits.values())[: settings.max_context_nodes]
    walk_hits = filter_hits_by_facets(walk_hits, facets)

    walked: dict[str, Any] = {"nodes": [], "relationships": [], "graph_walk_steps": []}
    try:
        walked = await walk_for_chat(
            walk_hits,
            search_query,
            document_ids=doc_ids or None,
            max_nodes=min(settings.max_context_nodes + 4, 18),
            max_hops=2,
        )
    except Exception as exc:
        add_warning(new_state, f"{layer} walk: {exc}")

    nodes_found = list(walked.get("nodes") or [])
    edges_found = list(walked.get("relationships") or [])
    allowed = _LAYER_LABELS.get(layer, frozenset())
    if allowed:
        nodes_found = [n for n in nodes_found if str(n.get("label") or "") in allowed or _node_layer(n) == layer]
    anomaly_nodes = _anomaly_nodes_from_layer(nodes_found) if layer == "L4" else []
    layer_result = {
        "layer": layer,
        "nodes_found": nodes_found,
        "edges_found": edges_found,
        "new_connections": [],
        "reasoning_step": (
            f"{_LAYER_REASONING.get(layer, layer)}: найдено {len(nodes_found)} узл., "
            f"{len(edges_found)} связей, Qdrant/keyword хитов {len(walk_hits)}"
        ),
        "situation_evaluation": (
            f"Оценка ситуации · {layer}: "
            f"{len(nodes_found)} узл., {len(edges_found)} св., "
            f"{len(walk_hits)} хитов — {_LAYER_REASONING.get(layer, layer)}"
        ),
        "agent_question": _LAYER_AGENT_QUESTIONS.get(layer, f"Что даст слой {layer}?"),
        "hit_count": len(walk_hits),
        "walk_step_count": len(walked.get("graph_walk_steps") or []),
        "anomaly_count": len(anomaly_nodes),
        "anomaly_evaluation": (
            f"L4 noise/outliers: {len(anomaly_nodes)} точек cluster_id=-1 требуют проверки"
            if anomaly_nodes
            else None
        ),
    }
    results = list(new_state.get("layer_results") or [])
    results.append(layer_result)
    new_state["layer_results"] = results
    new_state["accumulated_graph"] = _merge_subgraph(new_state, layer_result)
    new_state["agent_bus"] = _post_layer_bus_messages(
        new_state, layer, layer_result, loop_phase=loop_phase
    )

    bus_in = get_messages_for(new_state.get("agent_bus") or [], layer_to_agent_id(layer), round_num=round_num)
    acc = new_state.get("accumulated_graph") or {}
    add_trace(
        new_state,
        f"{layer.lower()}_agent",
        layer=layer,
        loop_index=loop_index,
        loop_total=LAYER_LOOP_TOTAL,
        loop_phase=loop_phase,
        round=round_num,
        max_rounds=max_rounds,
        node_count=len(nodes_found),
        rel_count=len(edges_found),
        hit_count=len(walk_hits),
        walk_step_count=layer_result["walk_step_count"],
        search_query=compact_text(search_query, 120),
        query_facets=facets.to_dict() or None,
        prior_user_question=compact_text(prior_user, 80) or None,
        prior_assistant_summary=compact_text(prior_assistant, 80) or None,
        reasoning=layer_result["reasoning_step"],
        situation_evaluation=layer_result["situation_evaluation"],
        agent_question=layer_result["agent_question"],
        anomaly_count=layer_result.get("anomaly_count") or 0,
        anomaly_evaluation=layer_result.get("anomaly_evaluation"),
        bus_in_count=len(bus_in),
        bus_messages=bus_summary(new_state.get("agent_bus"), limit=4),
        graph_snapshot=snapshot_for_trace(
            acc,
            doc_ids=list(new_state.get("candidate_doc_ids") or []),
        ),
    )
    return new_state


def _node_layer(node: dict[str, Any]) -> str:
    label = str(node.get("label") or "")
    return LABEL_LAYER.get(label, "L?")


def make_layer_runner(layer: str):
    async def _runner(
        state: OrchestratorState,
        gateway: GatewayClient,
        settings: AgentSettings,
    ) -> OrchestratorState:
        return await run_layer_agent(state, gateway, settings, layer)

    return _runner
