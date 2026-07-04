from __future__ import annotations

import asyncio
from typing import Any

from app.client import GatewayClient
from app.config import AgentSettings
from app.llm import AgentLLM
from app.state import MKGAgentState
from app.utils import add_warning, compact_text, normalize_dict, normalize_list, remaining_seconds, text_from_props

_VALID_MODES = {
    "audit_mode",
    "hypothesis_mode",
    "literature_review_mode",
    "recommendation_mode",
}

_PLANNER_PROMPT = """
Ты Scope Planner Agent для R&D knowledge graph горно-металлургической отрасли.
Верни только JSON object:
{
  "mode": "audit_mode|hypothesis_mode|literature_review_mode|recommendation_mode",
  "keywords": ["..."],
  "materials": ["..."],
  "processes": ["..."],
  "geography": ["domestic|foreign|..."],
  "years": ["..."],
  "requested_output": "...",
  "search_query": "короткий поисковый запрос"
}
Если mode уже задан во входе, сохрани его. Не выдумывай факты.
""".strip()

_ANALYZER_PROMPT = """
Ты Evidence Analyzer Agent. Анализируешь только переданные evidence из графа.
Верни только JSON object:
{
  "needs_more_evidence": false,
  "refined_search_query": "",
  "missing_evidence": [],
  "confidence": 0.0,
  "issues": [],
  "contradictions": [],
  "anomalies": [],
  "knowledge_gaps": [],
  "consensus_points": [],
  "disagreement_zones": [],
  "technology_coverage": {
    "domestic_only": [],
    "foreign_only": [],
    "both": [],
    "unknown": []
  },
  "related_experts": [],
  "related_labs": [],
  "warnings": []
}
Для каждого элемента указывай doc_id/node_id, если он есть во входе. Если данных мало, явно добавь knowledge_gaps.
Если evidence недостаточно для ответа, поставь needs_more_evidence=true и дай refined_search_query.
""".strip()

_BUILDER_PROMPT = """
Ты Report Builder Agent. Сформируй результат строго для выбранного режима.
Верни только JSON object:
{
  "summary": "короткий вывод на русском",
  "issues": [],
  "hypotheses": [],
  "recommendations": [],
  "literature_review": {},
  "warnings": []
}
Для audit_mode заполни issues.
Для hypothesis_mode заполни hypotheses: hypothesis, basis, supporting_evidence, contradictions, novelty, feasibility, confidence, next_experiments, rank.
Для literature_review_mode заполни literature_review: source_groups, domestic_only_technologies, foreign_only_technologies, consensus_points, disagreement_zones.
Для recommendation_mode заполни recommendations: similar_cases, adjacent_solutions, related_experts, related_labs, deep_dive_topics, reason.
Не добавляй утверждения без опоры на evidence; если данных мало, напиши это в summary и warnings.
""".strip()


def _fatal(state: MKGAgentState, node: str, message: str) -> MKGAgentState:
    new_state = dict(state)
    new_state["fatal_error"] = message
    new_state["timed_out_node"] = node if "timeout" in message.lower() else None
    add_warning(new_state, message)
    return new_state


def _should_stop(state: MKGAgentState) -> bool:
    return bool(state.get("fatal_error"))


async def capabilities_check(state: MKGAgentState, gateway: GatewayClient) -> MKGAgentState:
    new_state = dict(state)
    try:
        new_state["capabilities"] = await gateway.capabilities()
    except Exception as exc:
        add_warning(new_state, f"gateway capabilities недоступны: {exc}")
        new_state["capabilities"] = {}
    return new_state


async def llm_scope_planner(
    state: MKGAgentState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    timeout = min(settings.planner_timeout, remaining_seconds(new_state, settings.timeout_seconds))
    if timeout <= 0:
        return _fatal(new_state, "llm_scope_planner", "timeout: не осталось времени на llm_scope_planner")
    payload = {
        "query": new_state.get("query"),
        "requested_mode": new_state.get("requested_mode"),
        "user_role": new_state.get("user_role"),
    }
    try:
        scope = await llm.generate_json(
            instructions=_PLANNER_PROMPT,
            payload=payload,
            max_tokens=400,
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return _fatal(new_state, "llm_scope_planner", "timeout: llm_scope_planner не успел")
    except Exception as exc:
        return _fatal(new_state, "llm_scope_planner", f"LLM error in llm_scope_planner: {exc}")

    requested = new_state.get("requested_mode")
    mode = scope.get("mode") if isinstance(scope, dict) else None
    if requested:
        mode = requested
    if mode not in _VALID_MODES:
        mode = "hypothesis_mode"
    new_state["mode"] = mode
    new_state["scope"] = scope if isinstance(scope, dict) else {}
    return new_state


async def document_selector(
    state: MKGAgentState,
    gateway: GatewayClient,
    settings: AgentSettings,
) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    doc_ids = list(new_state.get("doc_ids") or [])
    if doc_ids:
        new_state["candidate_doc_ids"] = doc_ids[: settings.max_docs]
        new_state["docs"] = [{"id": doc_id} for doc_id in new_state["candidate_doc_ids"]]
        return new_state
    try:
        payload = await gateway.docs(page_size=settings.max_docs * 2)
    except Exception as exc:
        add_warning(new_state, f"список документов недоступен: {exc}")
        new_state["candidate_doc_ids"] = []
        new_state["docs"] = []
        return new_state
    docs = [
        item
        for item in payload.get("items", [])
        if item.get("status") == "loaded"
    ][: settings.max_docs]
    new_state["docs"] = docs
    new_state["candidate_doc_ids"] = [item["id"] for item in docs if item.get("id")]
    if not docs:
        add_warning(new_state, "нет документов со статусом loaded для анализа")
    return new_state


async def retrieval_search(
    state: MKGAgentState,
    gateway: GatewayClient,
    settings: AgentSettings,
) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    doc_ids = new_state.get("candidate_doc_ids") or []
    scope = normalize_dict(new_state.get("scope"))
    keywords = scope.get("keywords") if isinstance(scope.get("keywords"), list) else []
    search_query = (
        new_state.get("current_search_query")
        or scope.get("search_query")
        or " ".join([new_state.get("query", ""), *map(str, keywords[:4])]).strip()
    )
    new_state["current_search_query"] = str(search_query)
    if not doc_ids:
        new_state["search_hits"] = []
        return new_state

    async def run_one(doc_id: str) -> dict[str, Any]:
        return await gateway.search(doc_id, search_query, min(settings.search_limit, int(new_state.get("limit", 5))))

    results = await asyncio.gather(*(run_one(doc_id) for doc_id in doc_ids), return_exceptions=True)
    hits: list[dict[str, Any]] = []
    for doc_id, result in zip(doc_ids, results):
        if isinstance(result, Exception):
            add_warning(new_state, f"поиск по {doc_id} не выполнен: {result}")
            continue
        for hit in result.get("hits", []):
            item = dict(hit)
            item["doc_id"] = doc_id
            hits.append(item)
    hits.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    new_state["search_hits"] = hits[: settings.max_docs * settings.search_limit]
    if not hits:
        add_warning(new_state, "поиск не вернул релевантные фрагменты")
    return new_state


async def graph_context_loader(
    state: MKGAgentState,
    gateway: GatewayClient,
    settings: AgentSettings,
) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    hits = new_state.get("search_hits") or []
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for hit in hits:
        key = (str(hit.get("doc_id")), str(hit.get("node_id")))
        if key[0] and key[1] and key not in seen:
            unique.append(hit)
            seen.add(key)
        if len(unique) >= settings.max_context_nodes:
            break

    async def load_one(hit: dict[str, Any]) -> dict[str, Any]:
        detail = await gateway.node(str(hit["doc_id"]), str(hit["node_id"]))
        return {"hit": hit, "detail": detail}

    results = await asyncio.gather(*(load_one(hit) for hit in unique), return_exceptions=True)
    context: list[dict[str, Any]] = []
    for hit, result in zip(unique, results):
        if isinstance(result, Exception):
            add_warning(new_state, f"контекст узла {hit.get('node_id')} недоступен: {result}")
            context.append({"hit": hit, "detail": None})
        else:
            context.append(result)
    new_state["node_context"] = context
    return new_state


async def evidence_collector(state: MKGAgentState) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    evidence: list[dict[str, Any]] = list(new_state.get("evidence") or [])
    seen_evidence = {
        (str(item.get("doc_id")), str(item.get("node_id")))
        for item in evidence
        if item.get("doc_id") and item.get("node_id")
    }
    for item in new_state.get("node_context") or []:
        hit = item.get("hit") or {}
        detail = item.get("detail") or {}
        node = detail.get("node") or {}
        props = node.get("props") or hit.get("props") or {}
        evidence_key = (
            str(hit.get("doc_id") or detail.get("document_id") or ""),
            str(hit.get("node_id") or node.get("id") or ""),
        )
        if evidence_key in seen_evidence:
            continue
        neighbors = []
        for neighbor in detail.get("neighbors") or []:
            n_props = neighbor.get("props") or {}
            neighbors.append(
                {
                    "id": neighbor.get("id"),
                    "label": neighbor.get("label"),
                    "text": compact_text(text_from_props(n_props), 160),
                }
            )
        evidence.append(
            {
                "doc_id": hit.get("doc_id") or detail.get("document_id"),
                "node_id": hit.get("node_id") or node.get("id"),
                "label": hit.get("label") or node.get("label"),
                "layer": hit.get("layer") or detail.get("layer"),
                "score": hit.get("score"),
                "text": compact_text(hit.get("text") or detail.get("text") or text_from_props(props)),
                "neighbors": neighbors[:8],
            }
        )
        seen_evidence.add(evidence_key)
    new_state["evidence"] = evidence
    return new_state


async def llm_evidence_analyzer(
    state: MKGAgentState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    timeout = min(settings.analyzer_timeout, remaining_seconds(new_state, settings.timeout_seconds))
    if timeout <= 0:
        return _fatal(new_state, "llm_evidence_analyzer", "timeout: не осталось времени на llm_evidence_analyzer")
    payload = {
        "query": new_state.get("query"),
        "mode": new_state.get("mode"),
        "scope": new_state.get("scope", {}),
        "evidence": new_state.get("evidence", []),
    }
    try:
        analysis = await llm.generate_json(
            instructions=_ANALYZER_PROMPT,
            payload=payload,
            max_tokens=900,
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return _fatal(new_state, "llm_evidence_analyzer", "timeout: llm_evidence_analyzer не успел")
    except Exception as exc:
        return _fatal(new_state, "llm_evidence_analyzer", f"LLM error in llm_evidence_analyzer: {exc}")
    new_state["analysis"] = analysis if isinstance(analysis, dict) else {}
    for warning in normalize_list(new_state["analysis"].get("warnings")):
        value = warning.get("value") or warning.get("message")
        if value:
            add_warning(new_state, str(value))
    return new_state


async def route_by_mode(state: MKGAgentState) -> MKGAgentState:
    return state


def choose_mode(state: MKGAgentState) -> str:
    return str(state.get("mode") or "hypothesis_mode")


def choose_loop(state: MKGAgentState) -> str:
    return str(state.get("loop_decision") or "continue")


async def agent_loop_controller(state: MKGAgentState, settings: AgentSettings) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    analysis = normalize_dict(new_state.get("analysis"))
    retry_count = int(new_state.get("retry_count") or 0)
    evidence_count = len(new_state.get("evidence") or [])
    wants_more = bool(analysis.get("needs_more_evidence"))
    refined_query = analysis.get("refined_search_query")
    has_time = remaining_seconds(new_state, settings.timeout_seconds, reserve=1.0) > 0.4
    can_retry = retry_count < settings.max_agent_loops and has_time

    if can_retry and (wants_more or evidence_count < 2):
        new_state["retry_count"] = retry_count + 1
        new_state["loop_decision"] = "retry"
        used = list(new_state.get("used_search_queries") or [])
        previous_query = new_state.get("current_search_query")
        if previous_query:
            used.append(str(previous_query))
        new_state["used_search_queries"] = used
        if isinstance(refined_query, str) and refined_query.strip():
            new_state["current_search_query"] = refined_query.strip()
        else:
            missing = analysis.get("missing_evidence")
            missing_text = " ".join(str(item) for item in missing[:3]) if isinstance(missing, list) else ""
            new_state["current_search_query"] = f"{new_state.get('query', '')} {missing_text}".strip()
        add_warning(new_state, f"agent loop retry {new_state['retry_count']}: уточняю поиск по evidence")
        return new_state

    new_state["loop_decision"] = "continue"
    if wants_more and not can_retry:
        add_warning(new_state, "LLM запросила больше evidence, но лимит agent loop/time budget исчерпан")
    return new_state


async def literature_grouper(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    analysis = normalize_dict(new_state.get("analysis"))
    review = normalize_dict(new_state.get("mode_result")).get("literature_review")
    source_groups = []
    if isinstance(review, dict):
        source_groups = normalize_list(review.get("source_groups"))
    if not source_groups:
        source_groups = normalize_list(analysis.get("source_groups"))
    if not source_groups:
        source_groups = [
            {
                "method": item.get("label") or "unknown",
                "geography": "unknown",
                "detail_level": item.get("layer") or "unknown",
                "source_count": 1,
                "doc_id": item.get("doc_id"),
            }
            for item in (new_state.get("evidence") or [])[:8]
        ]
    new_state["source_groups"] = source_groups
    return new_state


async def technology_coverage_analyzer(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    analysis = normalize_dict(new_state.get("analysis"))
    coverage = normalize_dict(analysis.get("technology_coverage"))
    if not coverage:
        coverage = {
            "domestic_only": [],
            "foreign_only": [],
            "both": [],
            "unknown": [],
        }
    new_state["technology_coverage"] = coverage
    return new_state


async def consensus_detector(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    analysis = normalize_dict(new_state.get("analysis"))
    new_state["consensus_points"] = normalize_list(analysis.get("consensus_points"))
    new_state["disagreement_zones"] = normalize_list(analysis.get("disagreement_zones"))
    return new_state


async def pattern_discovery(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    patterns: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for item in new_state.get("evidence") or []:
        key = str(item.get("label") or item.get("layer") or "unknown")
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            patterns.append({"pattern": key, "supporting_evidence_count": count})
    new_state["patterns"] = patterns
    return new_state


async def expert_finder(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    analysis = normalize_dict(new_state.get("analysis"))
    experts = normalize_list(analysis.get("related_experts"))
    labs = normalize_list(analysis.get("related_labs"))
    for item in new_state.get("evidence") or []:
        for neighbor in item.get("neighbors") or []:
            label = str(neighbor.get("label") or "")
            if label == "Expert":
                experts.append(neighbor)
            if label in {"Organization", "Facility"}:
                labs.append(neighbor)
    new_state["related_experts"] = experts
    new_state["related_labs"] = labs
    return new_state


async def ranking_agent(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    result = normalize_dict(new_state.get("mode_result"))

    def as_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def as_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    hypotheses = normalize_list(result.get("hypotheses"))
    if hypotheses:
        hypotheses.sort(
            key=lambda item: (
                as_int(item.get("rank"), 999),
                -as_float(item.get("confidence"), 0.0),
            )
        )
        result["hypotheses"] = hypotheses
    recommendations = normalize_list(result.get("recommendations"))
    experts = normalize_list(new_state.get("related_experts"))
    labs = normalize_list(new_state.get("related_labs"))
    if recommendations and (experts or labs):
        first = dict(recommendations[0])
        if experts and not first.get("related_experts"):
            first["related_experts"] = experts
        if labs and not first.get("related_labs"):
            first["related_labs"] = labs
        recommendations[0] = first
    elif experts or labs:
        recommendations = [
            {
                "similar_cases": [],
                "adjacent_solutions": [],
                "related_experts": experts,
                "related_labs": labs,
                "deep_dive_topics": [],
                "reason": "Связанные эксперты и организации найдены в соседях evidence-графа.",
            }
        ]
    result["recommendations"] = recommendations
    new_state["mode_result"] = result
    return new_state


async def llm_mode_builder(
    state: MKGAgentState,
    llm: AgentLLM,
    settings: AgentSettings,
) -> MKGAgentState:
    if _should_stop(state):
        return state
    new_state = dict(state)
    timeout = min(settings.builder_timeout, remaining_seconds(new_state, settings.timeout_seconds))
    if timeout <= 0:
        return _fatal(new_state, "llm_mode_builder", "timeout: не осталось времени на llm_mode_builder")
    payload = {
        "query": new_state.get("query"),
        "mode": new_state.get("mode"),
        "scope": new_state.get("scope", {}),
        "evidence": new_state.get("evidence", []),
        "analysis": new_state.get("analysis", {}),
        "source_groups": new_state.get("source_groups", []),
        "technology_coverage": new_state.get("technology_coverage", {}),
        "consensus_points": new_state.get("consensus_points", []),
        "disagreement_zones": new_state.get("disagreement_zones", []),
        "patterns": new_state.get("patterns", []),
        "limit": new_state.get("limit", 5),
    }
    try:
        result = await llm.generate_json(
            instructions=_BUILDER_PROMPT,
            payload=payload,
            max_tokens=settings.llm_max_output_tokens,
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return _fatal(new_state, "llm_mode_builder", "timeout: llm_mode_builder не успел")
    except Exception as exc:
        return _fatal(new_state, "llm_mode_builder", f"LLM error in llm_mode_builder: {exc}")
    new_state["mode_result"] = result if isinstance(result, dict) else {}
    return new_state


async def final_report_builder(state: MKGAgentState) -> MKGAgentState:
    new_state = dict(state)
    result = normalize_dict(new_state.get("mode_result"))
    analysis = normalize_dict(new_state.get("analysis"))
    warnings = list(new_state.get("warnings") or [])
    for warning in normalize_list(result.get("warnings")):
        value = warning.get("value") or warning.get("message")
        if value and str(value) not in warnings:
            warnings.append(str(value))
    if new_state.get("fatal_error") and new_state["fatal_error"] not in warnings:
        warnings.append(str(new_state["fatal_error"]))
    if int(new_state.get("retry_count") or 0) > 0:
        warnings.append(f"agent loop выполнил {new_state.get('retry_count')} дополнительный поиск")
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        if new_state.get("fatal_error"):
            summary = "Агентный анализ не завершён: LLM-вызов завершился ошибкой или timeout."
        elif not new_state.get("evidence"):
            summary = "Нет достаточных данных из графа для аналитического ответа."
        else:
            summary = "Анализ завершён частично."
    new_state["final_response"] = {
        "mode": new_state.get("mode") or new_state.get("requested_mode") or "hypothesis_mode",
        "query": new_state.get("query", ""),
        "summary": summary,
        "issues": normalize_list(result.get("issues")) or normalize_list(analysis.get("issues")),
        "hypotheses": normalize_list(result.get("hypotheses")),
        "recommendations": normalize_list(result.get("recommendations")),
        "literature_review": normalize_dict(result.get("literature_review")),
        "evidence": normalize_list(new_state.get("evidence")),
        "warnings": warnings,
    }
    return new_state
