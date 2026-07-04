"""Общая логика чата: поиск, subgraph, артефакты, LLM."""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from mkg_core.answer_structure import CHAT_STRUCTURE_RULES, FAST_STRUCTURE_NOTE, chat_structure_rules
from mkg_core.config import get_settings
from mkg_core.embeddings import search_chat_retrieval
from mkg_core.query_classify import (
    classify_query_intent,
    conversational_system_note,
    is_conversational_query,
    retrieval_confidence_ok,
)
from mkg_core.query_facets import reliability_from_props, source_date_from_props
from mkg_core.comparison import is_comparison_query, run_comparison_analysis
from mkg_core.graph_traversal import discover_new_connections, has_graph_data, walk_for_chat
from mkg_core.graph_meta import enrich_graph_for_persistence
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.llm import YandexLLMClient
from mkg_core.ontology import LABEL_LAYER
from mkg_core.text_sanitize import sanitize_user_facing_text

from app.collab_db import get_role_prompt
from app.data_access import allowed_classifications
from app.role_prompts import CHAT_OUTPUT_RULES, default_prompt
from app.roles import get_role
from app.schemas import ChatArtifact, ChatCompleteOut, ContextGraphOut, GraphNode, GraphRelationship, ChatSourceOut
from app.storage import get_repo

_ARTIFACTS_RE = re.compile(r"```mkg-artifacts\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
_CHART_HINTS = re.compile(
    r"(график|диаграмм|chart|plot|визуализ|сравн|распредел|динамик|тренд|статистик)",
    re.IGNORECASE,
)
_ORCHESTRATOR_PLACEHOLDER_RE = re.compile(
    r"^Найдено \d+ узлов и \d+ связей по слоям MKG\.\s*$"
)

_LAYER_AGENT_QUESTIONS: dict[str, str] = {
    "L1": "Какие материалы, процессы и оборудование связаны с запросом?",
    "L2": "Кто и где упоминается в контексте документов?",
    "L3": "Какие текстовые фрагменты релевантны вопросу?",
    "L4": "Какие факты, утверждения и аномалии связаны с темой?",
    "L5": "Как классифицированы и верифицированы найденные данные?",
    "L6": "Какие технологические и экономические показатели затронуты?",
}

_LAYER_SITUATION: dict[str, str] = {
    "L1": "Material/Entity: материалы, процессы, оборудование",
    "L2": "Context: документы, эксперты, организации",
    "L3": "Text: текстовые фрагменты и контекст",
    "L4": "Facts: утверждения, кластеры, аномалии",
    "L5": "Classification: верификация и грифы",
    "L6": "TEP: технологические и экономические показатели",
}

FAST_SEARCH_LIMIT = 6
FAST_MAX_TOKENS = 256
FAST_LLM_TIMEOUT_S = 3.5

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")

def _detect_reply_language(message: str, ui_lang: str | None = None) -> str:
    """Return 'en' or 'ru' for LLM answer language."""
    text = (message or "").strip()
    if not text:
        return "en" if str(ui_lang or "").lower().startswith("en") else "ru"
    cyr = len(_CYRILLIC_RE.findall(text))
    lat = len(_LATIN_RE.findall(text))
    if cyr > lat and cyr >= 3:
        return "ru"
    if lat > cyr and lat >= 3:
        return "en"
    return "en" if str(ui_lang or "").lower().startswith("en") else "ru"


def _reply_language_instruction(lang: str) -> str:
    if lang == "en":
        return (
            "Language: answer entirely in English — same language as the user's question. "
            "Use ## section headers in English."
        )
    return (
        "Язык: отвечай полностью на русском — на том же языке, что и вопрос пользователя. "
        "Заголовки разделов ## — на русском."
    )


def _apply_reply_language(system: str, message: str, ui_lang: str | None = None) -> tuple[str, str]:
    """Append language + localized structure rules; return (system, lang code)."""
    lang = _detect_reply_language(message, ui_lang)
    rules = chat_structure_rules(lang)
    if rules not in system:
        system = system.replace(CHAT_STRUCTURE_RULES, rules) if CHAT_STRUCTURE_RULES in system else system
        if rules not in system:
            system += f"\n\n{rules}"
    system += f"\n\n{_reply_language_instruction(lang)}"
    return system, lang


def _count_anomalies(
    hits: list[dict[str, Any]] | None,
    walked: dict[str, Any] | None = None,
) -> int:
    count = 0
    for h in hits or []:
        if h.get("is_anomaly"):
            count += 1
            continue
        cid = h.get("cluster_id")
        try:
            if int(cid) == -1:
                count += 1
        except (TypeError, ValueError):
            pass
    for node in (walked or {}).get("nodes") or []:
        props = node.get("props") or {}
        if props.get("is_anomaly"):
            count += 1
            continue
        cid = props.get("cluster_id")
        try:
            if int(cid) == -1:
                count += 1
        except (TypeError, ValueError):
            pass
    return count


def _append_anomaly_agent_trace(
    trace: list[dict[str, Any]],
    hits: list[dict[str, Any]] | None,
    walked: dict[str, Any] | None,
    *,
    t0: float,
    anomaly_count: int | None = None,
) -> None:
    """Anomaly detection agent steps for «Работа агентов» (always visible; skipped when none)."""
    if any(str(t.get("step") or "").startswith("anomaly_") for t in trace):
        return
    count = anomaly_count if anomaly_count is not None else _count_anomalies(hits, walked)
    skipped = count <= 0
    elapsed = int((time.perf_counter() - t0) * 1000)
    l4_anomaly_hits = sum(
        1
        for h in hits or []
        if h.get("is_anomaly") or str(h.get("cluster_id")) == "-1"
    )
    for t in trace:
        if t.get("step") == "l4_agent":
            t["anomaly_count"] = count
            break
    situation = (
        f"L4 anomaly_mode: {count} noise/outlier точек"
        if count > 0
        else "L4 anomaly_mode: аномалий не обнаружено (HDBSCAN noise / cluster_id=-1)"
    )
    trace.extend(
        [
            {
                "step": "anomaly_seed_loader",
                "anomaly_count": count,
                "mode": "anomaly_mode",
                "layer": "L4",
                "skipped": skipped,
                "elapsed_ms": elapsed,
            },
            {
                "step": "anomaly_qdrant_refine",
                "hit_count": l4_anomaly_hits,
                "anomaly_count": count,
                "mode": "anomaly_mode",
                "layer": "L4",
                "skipped": skipped,
                "elapsed_ms": elapsed,
            },
            {
                "step": "anomaly_mode_builder",
                "anomaly_count": count,
                "mode": "anomaly_mode",
                "layer": "L4",
                "loop_phase": "dialog_trace",
                "round": 0,
                "skipped": skipped,
                "agent_question": "Какие L4-факты — аномалии (HDBSCAN noise) и почему?",
                "situation_evaluation": situation,
                "reasoning": situation,
                "elapsed_ms": elapsed,
            },
        ]
    )


def _orchestrator_anomaly_count(
    trace: list[dict[str, Any]],
    layer_results: list[dict[str, Any]] | None,
) -> int:
    count = 0
    for t in trace:
        if t.get("step") == "l4_agent":
            count = max(count, int(t.get("anomaly_count") or 0))
    for lr in layer_results or []:
        if str(lr.get("layer") or "").upper() == "L4":
            count = max(count, int(lr.get("anomaly_count") or 0))
    return count


def _append_orchestrator_anomaly_trace(
    trace: list[dict[str, Any]],
    layer_results: list[dict[str, Any]] | None,
    *,
    t0: float,
) -> None:
    """Ensure anomaly agent appears in orchestrator trace for UI agent bus."""
    _append_anomaly_agent_trace(
        trace,
        None,
        None,
        t0=t0,
        anomaly_count=_orchestrator_anomaly_count(trace, layer_results),
    )


_COMPARISON_SECTION_MARKERS = ("## Сравнение технологий", "## Technology comparison")


async def _inject_comparison_table(
    message: str,
    reply: str,
    *,
    document_ids: list[str] | None,
    hits: list[dict[str, Any]],
    walked: dict[str, Any] | None,
    trace: list[dict[str, Any]],
    t0: float,
) -> str:
    """Добавить markdown-таблицу сравнения, если её ещё нет в ответе."""
    try:
        result = await run_comparison_analysis(
            message.strip(),
            document_ids=document_ids,
            hits=hits,
            walked_graph=walked,
            use_llm=True,
        )
    except Exception as exc:
        trace.append(
            {
                "step": "comparison_analysis",
                "skipped": True,
                "error": str(exc)[:160],
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
        return reply

    trace.append(
        {
            "step": "comparison_analysis",
            "row_count": len(result.get("rows") or []),
            "partial": result.get("partial", False),
            "gap_count": result.get("gap_count", 0),
            "llm_filled": result.get("llm_filled", False),
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }
    )
    md = str(result.get("markdown") or "").strip()
    if not md:
        return reply
    if any(marker in reply for marker in _COMPARISON_SECTION_MARKERS):
        return reply
    body = reply.strip()
    if body:
        return f"{body}\n\n{md}"
    return md


def _wants_comparison(message: str, speed_mode: str) -> bool:
    return speed_mode == "compare" or is_comparison_query(message)


def _format_user_prompt_with_history(
    message: str,
    history: list[dict[str, str]] | None,
) -> tuple[str, dict[str, Any]]:
    """Собрать промпт с историей диалога; при длинной нити — сжать середину."""
    turns = list(history or [])
    memory_meta: dict[str, Any] = {"turn_count": len(turns), "truncated": False}
    if len(turns) > 10:
        memory_meta["truncated"] = True
        turns = turns[:2] + turns[-8:]
    lines: list[str] = []
    if memory_meta["truncated"]:
        lines.append("(Ранние реплики сокращены — сохранён контекст последних сообщений.)")
    for turn in turns:
        label = "Пользователь" if turn.get("role") == "user" else "Ассистент"
        content = str(turn.get("content") or "").strip()
        if content:
            lines.append(f"{label}: {content[:2000]}")
    lines.append(f"Пользователь: {message.strip()}")
    return "\n\n".join(lines), memory_meta


def _append_layer_situation_trace(
    trace: list[dict[str, Any]],
    walked: dict[str, Any],
    *,
    t0: float,
) -> list[dict[str, Any]]:
    """L1–L6 оценка ситуации по узлам обхода графа (для UI «Агенты по слоям»)."""
    layer_nodes: dict[str, int] = {f"L{i}": 0 for i in range(1, 7)}
    layer_rels: dict[str, int] = {f"L{i}": 0 for i in range(1, 7)}
    for node in walked.get("nodes") or []:
        layer = LABEL_LAYER.get(str(node.get("label") or ""), "")
        if layer in layer_nodes:
            layer_nodes[layer] += 1
    node_layer_by_id = {
        str(n.get("id") or ""): LABEL_LAYER.get(str(n.get("label") or ""), "")
        for n in walked.get("nodes") or []
    }
    for rel in walked.get("relationships") or []:
        from_layer = node_layer_by_id.get(str(rel.get("from") or ""), "")
        to_layer = node_layer_by_id.get(str(rel.get("to") or ""), "")
        for layer in {from_layer, to_layer}:
            if layer in layer_rels:
                layer_rels[layer] += 1
    for loop_index, layer in enumerate(("L1", "L2", "L3", "L4", "L5", "L6"), start=1):
        n_count = layer_nodes[layer]
        r_count = layer_rels[layer]
        if n_count == 0 and r_count == 0:
            situation = f"Слой {layer}: данных в обходе nет — {_LAYER_SITUATION.get(layer, layer)}"
            skipped = True
        else:
            situation = (
                f"Слой {layer}: {n_count} узл., {r_count} св. — "
                f"{_LAYER_SITUATION.get(layer, layer)}"
            )
            skipped = False
        trace.append(
            {
                "step": f"{layer.lower()}_agent",
                "layer": layer,
                "loop_index": loop_index,
                "loop_total": 6,
                "loop_phase": "dialog_trace",
                "round": 0,
                "max_rounds": 1,
                "node_count": n_count,
                "rel_count": r_count,
                "situation_evaluation": situation,
                "reasoning": situation,
                "agent_question": _LAYER_AGENT_QUESTIONS.get(layer, f"Что даст слой {layer}?"),
                "skipped": skipped,
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
    return trace


def _expanded_to_context_graph(expanded: dict[str, Any]) -> ContextGraphOut:
    if not expanded.get("nodes"):
        return ContextGraphOut(nodes=[], relationships=[], seed_count=0, document_ids=[])
    deduped = dedupe_graph_payload(
        GraphPayload(
            nodes=list(expanded.get("nodes") or []),
            relationships=list(expanded.get("relationships") or []),
        )
    )
    nodes_out = [
        GraphNode(
            id=str(n["id"]),
            label=str(n.get("label") or ""),
            props=dict(n.get("props") or {}),
        )
        for n in deduped.nodes
    ]
    rels_out = [
        GraphRelationship(
            type=str(r.get("type") or ""),
            from_=str(r.get("from") or ""),
            to=str(r.get("to") or ""),
            props=dict(r.get("props") or {}),
        )
        for r in deduped.relationships
    ]
    return ContextGraphOut(
        nodes=nodes_out,
        relationships=rels_out,
        seed_count=int(expanded.get("seed_count") or 0),
        document_ids=list(expanded.get("document_ids") or []),
        graph_walk_steps=list(expanded.get("graph_walk_steps") or []),
        walk_path=list(expanded.get("walk_path") or []),
    )


def _hits_context_block(hits: list[dict[str, Any]], *, limit: int = 8) -> str:
    if not hits:
        return ""
    lines = []
    for i, h in enumerate(hits[:limit], 1):
        doc = h.get("document_id") or h.get("doc_id") or "?"
        nid = h.get("neo4j_node_id") or h.get("node_id") or "?"
        text = (h.get("text") or h.get("snippet") or "")[:500]
        layer = h.get("layer") or ""
        meta: list[str] = []
        if layer:
            meta.append(str(layer))
        factors = h.get("retrieval_factors") or []
        if factors:
            meta.append("+".join(str(f) for f in factors))
        src = h.get("retrieval_source") or ""
        if src:
            meta.append(str(src))
        cid = h.get("cluster_id")
        if cid is not None:
            meta.append(f"cluster={cid}")
        if h.get("is_anomaly"):
            meta.append("anomaly")
        suffix = f" · {' · '.join(meta)}" if meta else ""
        lines.append(f"{i}. [{doc} · {nid}{suffix}] {text}")
    return "Фрагменты MKG (L3 эмбеддинги + L4 кластеры):\n" + "\n".join(lines)


def _graph_context_block(graph: ContextGraphOut) -> str:
    if not graph.nodes:
        return ""
    lines = ["Узлы графа MKG (последовательный обход):"]
    walk_steps = graph.graph_walk_steps or []
    if walk_steps:
        lines.append("Цепочка обхода:")
        for ws in walk_steps[:30]:
            order = ws.get("order", "?")
            action = ws.get("action", "")
            label = ws.get("label") or "?"
            nid = ws.get("node_id") or "?"
            rel = ws.get("rel_type") or ""
            snippet = ws.get("snippet") or ""
            if action == "seed_load":
                lines.append(f"  {order}. ★ SEED [{label} · {nid}] {snippet[:200]}")
            else:
                from_id = ws.get("from_id") or "?"
                lines.append(
                    f"  {order}. hop{ws.get('hop', '?')} [{from_id}] -[{rel}]-> [{label} · {nid}] {snippet[:160]}"
                )
        lines.append("")
    for i, node in enumerate(graph.nodes[:24], 1):
        props = node.props or {}
        text = (
            props.get("name_ru")
            or props.get("raw_text_ru")
            or props.get("quote")
            or props.get("text")
            or props.get("title_ru")
            or node.label
        )
        seed = " ★" if props.get("_seed") else ""
        nid = props.get("neo4j_node_id") or node.id
        lines.append(f"{i}. [{node.label} · {nid}{seed}] {str(text)[:320]}")
    traverse_steps = [
        s for s in (graph.graph_walk_steps or []) if str(s.get("action") or "") == "traverse"
    ]
    if traverse_steps:
        lines.append("\nШаги обхода:")
        for s in traverse_steps[:12]:
            lines.append(
                f"  {s.get('order', '?')}. ({s.get('from_id')}) -[{s.get('rel_type')}]-> ({s.get('to_id')})"
            )
    elif graph.relationships:
        lines.append("\nСвязи обхода:")
        for rel in graph.relationships[:12]:
            lines.append(f"  ({rel.from_}) -[{rel.type}]-> ({rel.to})")
    return "\n".join(lines)


def parse_artifacts_from_reply(text: str) -> tuple[str, list[ChatArtifact]]:
    """Извлечь блок ```mkg-artifacts из ответа LLM."""
    match = _ARTIFACTS_RE.search(text)
    if not match:
        return text, []
    clean = (text[: match.start()] + text[match.end() :]).strip()
    try:
        raw = json.loads(match.group(1))
        if not isinstance(raw, list):
            return clean, []
        artifacts: list[ChatArtifact] = []
        for item in raw:
            if isinstance(item, dict) and item.get("type"):
                artifacts.append(ChatArtifact(**item))
        return clean, artifacts
    except (json.JSONDecodeError, TypeError, ValueError):
        return clean, []


def auto_artifacts(message: str, hits: list[dict[str, Any]]) -> list[ChatArtifact]:
    """Авто-графики из Qdrant-хитов, если пользователь просит визуализацию."""
    artifacts: list[ChatArtifact] = []
    if not hits:
        return artifacts
    wants_chart = bool(_CHART_HINTS.search(message))
    if wants_chart and len(hits) >= 1:
        labels = []
        scores = []
        for i, h in enumerate(hits[:10], 1):
            label = str(h.get("label") or "фрагмент")[:24]
            doc = str(h.get("document_id") or h.get("doc_id") or "")[-8:]
            labels.append(f"{label} ({doc})" if doc else label)
            scores.append(round(float(h.get("score") or 0), 3))
        artifacts.append(
            ChatArtifact(
                type="chart",
                title="Релевантность фрагментов MKG",
                chart_type="bar",
                labels=labels,
                datasets=[{"label": "Score", "data": scores, "backgroundColor": "#0071e3"}],
            )
        )
    if wants_chart and len(hits) >= 2:
        layer_counts: dict[str, int] = defaultdict(int)
        for h in hits:
            layer_counts[str(h.get("layer") or "L?")] += 1
        artifacts.append(
            ChatArtifact(
                type="chart",
                title="Слои найденных узлов",
                chart_type="doughnut",
                labels=list(layer_counts.keys()),
                datasets=[
                    {
                        "label": "Узлы",
                        "data": list(layer_counts.values()),
                        "backgroundColor": ["#0288d1", "#7b1fa2", "#546e7a", "#ef6c00", "#c62828", "#2e7d32"],
                    }
                ],
            )
        )
    if wants_chart and hits:
        scores = [float(h.get("score") or 0) for h in hits[:12]]
        if scores:
            w, h = 320, 80
            pts = []
            mx = max(scores) or 1
            for i, s in enumerate(scores):
                x = 8 + i * ((w - 16) / max(len(scores) - 1, 1))
                y = h - 8 - (s / mx) * (h - 16)
                pts.append(f"{x:.1f},{y:.1f}")
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                f'<polyline fill="none" stroke="#0071e3" stroke-width="2" points="{" ".join(pts)}"/>'
                f"</svg>"
            )
            artifacts.append(
                ChatArtifact(
                    type="image",
                    title="Тренд релевантности",
                    format="svg",
                    content=svg,
                )
            )
    return artifacts


def enrich_search_hits(hits: list[dict[str, Any]]) -> list[ChatSourceOut]:
    """Добавить имена файлов и ссылки на Markdown для Qdrant-хитов."""
    repo = get_repo()
    out: list[ChatSourceOut] = []
    seen: set[tuple[str, str]] = set()
    for h in hits:
        doc_id = str(h.get("document_id") or h.get("doc_id") or "").strip()
        node_id = str(h.get("node_id") or h.get("neo4j_node_id") or "").strip()
        if not doc_id:
            continue
        key = (doc_id, node_id or str(h.get("text") or "")[:80])
        if key in seen:
            continue
        seen.add(key)
        rec = repo.get(doc_id) or {}
        md_file = str(h.get("md_file") or "") or repo.markdown_relative_path(doc_id)
        props = h.get("props") if isinstance(h.get("props"), dict) else {}
        out.append(
            ChatSourceOut(
                document_id=doc_id,
                file_name=str(rec.get("file_name") or doc_id),
                node_id=node_id,
                label=str(h.get("label") or ""),
                layer=str(h.get("layer") or ""),
                score=float(h.get("score") or 0),
                text=str(h.get("text") or h.get("snippet") or "")[:500],
                md_file=md_file,
                md_url=f"/api/v1/documents/{doc_id}/markdown",
                extraction_confidence=reliability_from_props(props),
                source_date=source_date_from_props(props),
            )
        )
    return out


def _evidence_to_sources(
    evidence: list[dict[str, Any]] | None,
    layer_results: list[dict[str, Any]] | None,
) -> list[ChatSourceOut]:
    """Источники из evidence / layer_results agents service."""
    repo = get_repo()
    out: list[ChatSourceOut] = []
    seen: set[tuple[str, str]] = set()

    def _push(
        *,
        doc_id: str,
        node_id: str = "",
        file_name: str = "",
        label: str = "",
        layer: str = "",
        score: float = 0,
        text: str = "",
        props: dict[str, Any] | None = None,
    ) -> None:
        doc_id = doc_id.strip()
        if not doc_id:
            return
        key = (doc_id, node_id or text[:80])
        if key in seen:
            return
        seen.add(key)
        rec = repo.get(doc_id) or {}
        md_file = repo.markdown_relative_path(doc_id)
        node_props = props or {}
        out.append(
            ChatSourceOut(
                document_id=doc_id,
                file_name=file_name or str(rec.get("file_name") or doc_id),
                node_id=node_id,
                label=label,
                layer=layer,
                score=score,
                text=text[:500],
                md_file=md_file,
                md_url=f"/api/v1/documents/{doc_id}/markdown",
                extraction_confidence=reliability_from_props(node_props),
                source_date=source_date_from_props(node_props),
            )
        )

    for ev in evidence or []:
        ev_props = ev.get("props") if isinstance(ev.get("props"), dict) else {}
        _push(
            doc_id=str(ev.get("doc_id") or ev.get("document_id") or ""),
            node_id=str(ev.get("node_id") or ""),
            file_name=str(ev.get("file_name") or ""),
            label=str(ev.get("label") or ""),
            layer=str(ev.get("layer") or ""),
            score=float(ev.get("score") or 0),
            text=str(ev.get("text") or ev.get("quote") or ""),
            props=ev_props,
        )
    for lr in layer_results or []:
        for node in lr.get("nodes_found") or []:
            props = node.get("props") or {}
            _push(
                doc_id=str(props.get("_doc_id") or props.get("document_id") or props.get("source_doc_id") or ""),
                node_id=str(node.get("id") or ""),
                label=str(node.get("label") or ""),
                layer=str(lr.get("layer") or props.get("layer") or ""),
                text=str(props.get("quote") or props.get("raw_text_ru") or props.get("name_ru") or props.get("text") or ""),
                props=props,
            )
    return out[:8]


def _format_agent_summary(result: dict[str, Any]) -> str:
    """Собрать пользовательский текст из ответа LangGraph."""
    parts: list[str] = []
    summary = sanitize_user_facing_text(str(result.get("summary") or "").strip())
    if summary:
        parts.append(summary)
    hypotheses = result.get("hypotheses") or []
    if hypotheses:
        lines = [
            f"{i + 1}. {h.get('title') or h.get('text') or json.dumps(h, ensure_ascii=False)}"
            for i, h in enumerate(hypotheses)
        ]
        parts.append("Гипотезы:\n" + "\n".join(lines))
    recommendations = result.get("recommendations") or []
    if recommendations:
        lines = [
            f"{i + 1}. {x.get('title') or x.get('text') or json.dumps(x, ensure_ascii=False)}"
            for i, x in enumerate(recommendations)
        ]
        parts.append("Рекомендации:\n" + "\n".join(lines))
    anomalies = result.get("anomalies") or []
    if anomalies:
        lines = []
        for i, a in enumerate(anomalies):
            title = a.get("text") or a.get("node_id") or a.get("label") or "узел"
            reason = a.get("explanation") or a.get("anomaly_reason") or ""
            lines.append(f"{i + 1}. {title}" + (f" — {reason}" if reason else ""))
        parts.append("Аномалии:\n" + "\n".join(lines))
    return sanitize_user_facing_text("\n\n".join(parts).strip())


def _is_weak_orchestrator_reply(text: str) -> bool:
    cleaned = sanitize_user_facing_text(str(text or "").strip())
    if not cleaned:
        return True
    if _ORCHESTRATOR_PLACEHOLDER_RE.match(cleaned):
        return True
    if cleaned == "Недостаточно данных из графа для ответа.":
        return True
    return "##" not in cleaned and len(cleaned) < 120


def _layer_results_context_block(layer_results: list[dict[str, Any]] | None) -> str:
    lines: list[str] = []
    for layer_result in layer_results or []:
        layer = str(layer_result.get("layer") or "?").upper()
        for node in (layer_result.get("nodes_found") or [])[:4]:
            props = node.get("props") or {}
            text = (
                props.get("name_ru")
                or props.get("quote")
                or props.get("raw_text_ru")
                or props.get("text")
                or ""
            )
            if text:
                lines.append(f"[{layer} · {node.get('label') or '?'}] {str(text)[:220]}")
    if not lines:
        return ""
    return "Контекст слоёв L1–L6 (фрагменты, без техметок):\n" + "\n".join(lines[:24])


async def _orchestrator_dialog_fallback(
    result: dict[str, Any],
    message: str,
    role_id: str,
    *,
    history: list[dict[str, str]] | None,
    graph: ContextGraphOut | None,
) -> str | None:
    """Диалоговый LLM с собранным графом, если synthesizer вернул заглушку."""
    if not _is_weak_orchestrator_reply(_format_agent_summary(result)):
        return None
    has_graph = bool(graph and graph.nodes)
    has_layers = bool(result.get("layer_results"))
    if not has_graph and not has_layers:
        return None

    role = get_role(role_id)
    if not role:
        return None
    custom = await get_role_prompt(role_id)
    system = (custom or default_prompt(role_id)).strip()
    if CHAT_OUTPUT_RULES not in system:
        system += f"\n\n{CHAT_OUTPUT_RULES}"
    system += f"\n\n{CHAT_STRUCTURE_RULES}"

    context_parts: list[str] = []
    layer_block = _layer_results_context_block(result.get("layer_results"))
    if layer_block:
        context_parts.append(layer_block)
    if graph:
        graph_block = _graph_context_block(graph)
        if graph_block:
            context_parts.append(graph_block)

    user_prompt, _ = _format_user_prompt_with_history(message, history)
    if context_parts:
        context_block = "\n\n---\n\n".join(context_parts)
        user_prompt = f"{context_block}\n\n---\n\n{user_prompt}"

    try:
        llm = YandexLLMClient.instance()
        reply = await llm.chat(system, user_prompt, temperature=0.35, max_tokens=1024)
    except Exception:
        return None
    text = sanitize_user_facing_text((reply or "").strip())
    return text or None


async def _agent_result_to_chat_out(
    result: dict[str, Any],
    *,
    include_graph: bool,
    t0: float,
    history: list[dict[str, str]] | None = None,
    message: str = "",
    role_id: str = "",
) -> ChatCompleteOut:
    trace = list(result.get("trace") or [])
    trace.insert(0, {"step": "chat_role", "pipeline": "orchestrator_mode", "elapsed_ms": 0})
    memory_meta = _format_user_prompt_with_history("", history)[1]
    if not any(t.get("step") == "chat_memory" for t in trace):
        if memory_meta.get("turn_count"):
            trace.insert(
                1,
                {
                    "step": "chat_memory",
                    "turn_count": memory_meta["turn_count"],
                    "truncated": memory_meta.get("truncated", False),
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                },
            )
    graph_raw = result.get("graph")
    graph = ContextGraphOut(**graph_raw) if include_graph and graph_raw else None
    layer_results = result.get("layer_results") or None
    reply = _format_agent_summary(result)
    if _is_weak_orchestrator_reply(reply) and message.strip() and role_id:
        fallback = await _orchestrator_dialog_fallback(
            result,
            message.strip(),
            role_id,
            history=history,
            graph=graph,
        )
        if fallback:
            reply = fallback
    if not reply:
        reply = sanitize_user_facing_text(str(result.get("query") or "").strip())
    _append_orchestrator_anomaly_trace(trace, layer_results, t0=t0)
    timing_ms = int(result.get("elapsed_ms") or int((time.perf_counter() - t0) * 1000))
    return ChatCompleteOut(
        reply=reply,
        trace=trace,
        graph=graph,
        artifacts=[],
        sources=_evidence_to_sources(result.get("evidence"), layer_results),
        layer_results=layer_results,
        timing_ms=timing_ms,
        speed_mode="full",
    )


async def _try_orchestrator_chat(
    message: str,
    role_id: str,
    *,
    history: list[dict[str, str]] | None,
    include_graph: bool,
    search_limit: int,
    document_ids: list[str] | None,
    t0: float,
) -> ChatCompleteOut | None:
    """Внутренний L1–L6 оркестратор для ролей с can_run_agents."""
    role = get_role(role_id)
    if not role or not role.get("can_run_agents"):
        return None
    try:
        from app.agents_proxy import proxy_agents_run
        from app.roles import agents_user_role

        result = await proxy_agents_run(
            query=message.strip(),
            mode="orchestrator_mode",
            doc_ids=[d for d in (document_ids or []) if d] or None,
            user_role=agents_user_role(role_id),
            limit=search_limit,
            history=history,
        )
        return await _agent_result_to_chat_out(
            result,
            include_graph=include_graph,
            t0=t0,
            history=history,
            message=message.strip(),
            role_id=role_id,
        )
    except Exception:
        return None


async def run_direct_conversational_reply(
    message: str,
    role_id: str,
    *,
    history: list[dict[str, str]] | None = None,
    speed_mode: str = "full",
    ui_lang: str | None = None,
) -> ChatCompleteOut | None:
    """Короткий ответ на приветствие / meta без RAG и оркестратора."""
    intent = classify_query_intent(message.strip())
    if not intent:
        return None

    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        raise HTTPException(
            status_code=503,
            detail="LLM не настроен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID",
        )

    t0 = time.perf_counter()
    custom = await get_role_prompt(role_id)
    system = (custom or default_prompt(role_id)).strip()
    system, reply_lang = _apply_reply_language(system, message.strip(), ui_lang)
    system += f"\n\n{conversational_system_note(intent, lang=reply_lang)}"

    trace: list[dict[str, Any]] = [
        {
            "step": "chat_role",
            "role_id": role_id,
            "name_ru": role["name_ru"],
            "pipeline": "direct",
            "speed_mode": speed_mode,
            "elapsed_ms": 0,
        },
        {
            "step": "direct_reply",
            "intent": intent,
            "skipped_retrieval": True,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        },
    ]
    user_prompt, memory_meta = _format_user_prompt_with_history(message, history)
    if memory_meta.get("turn_count"):
        trace.append(
            {
                "step": "chat_memory",
                "turn_count": memory_meta["turn_count"],
                "truncated": memory_meta.get("truncated", False),
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )

    try:
        llm = YandexLLMClient.instance()
        reply = await asyncio.wait_for(
            llm.chat(system, user_prompt, temperature=0.4, max_tokens=180),
            timeout=8.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Прямой ответ: превышен лимит времени LLM") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {exc}") from exc

    text = sanitize_user_facing_text((reply or "").strip())
    if not text:
        raise HTTPException(status_code=502, detail="LLM вернул пустой ответ")

    trace.append(
        {
            "step": "llm_compose",
            "pipeline": "direct",
            "intent": intent,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }
    )
    timing_ms = int((time.perf_counter() - t0) * 1000)
    return ChatCompleteOut(
        reply=text,
        trace=trace,
        graph=None,
        artifacts=[],
        sources=[],
        timing_ms=timing_ms,
        speed_mode="direct",
    )


def _guard_retrieval_hits(hits: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Отбросить слабые/нерелевантные хиты для коротких бытовых запросов."""
    if is_conversational_query(query):
        return []
    if not retrieval_confidence_ok(hits, query):
        return []
    return hits


async def run_dialog_fast(
    message: str,
    role_id: str,
    *,
    history: list[dict[str, str]] | None = None,
    system_prompt: str | None = None,
    search_limit: int = FAST_SEARCH_LIMIT,
    document_ids: list[str] | None = None,
    llm_timeout: float = FAST_LLM_TIMEOUT_S,
    max_tokens: int = FAST_MAX_TOKENS,
    ui_lang: str | None = None,
) -> ChatCompleteOut:
    """Облегчённый RAG-диалог: Qdrant L3+L4 → короткий ответ LLM (~3–4 с)."""
    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        raise HTTPException(
            status_code=503,
            detail="LLM не настроен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID",
        )

    t0 = time.perf_counter()
    custom = await get_role_prompt(role_id)
    system = (system_prompt or custom or default_prompt(role_id)).strip()
    if CHAT_OUTPUT_RULES not in system:
        system += f"\n\n{CHAT_OUTPUT_RULES}"
    system, _reply_lang = _apply_reply_language(system, message.strip(), ui_lang)
    system += (
        "\n\nРежим «Быстрый ответ»: Qdrant L3+L4+mkg_entities (материалы/процессы) + keyword-fallback по графу; "
        "оркестратор L1–L6 не запускается. "
        "Дай краткий точный ответ по найденным фрагментам; "
        "каждый раздел ## — 1–2 коротких пункта, «Сводка» — 2–3 предложения; "
        "без длинных рассуждений и без блоков mkg-artifacts.\n\n"
        + FAST_STRUCTURE_NOTE
    )
    comparison_mode = _wants_comparison(message, "fast")
    if comparison_mode:
        system += (
            "\n\nПользователь просит сравнение технологий. Дай краткую сводку (2–3 предложения); "
            "таблица сравнения будет добавлена автоматически из графа MKG."
        )

    trace: list[dict[str, Any]] = [
        {
            "step": "chat_role",
            "role_id": role_id,
            "name_ru": role["name_ru"],
            "pipeline": "fast",
            "speed_mode": "fast",
            "elapsed_ms": 0,
        },
    ]
    user_prompt_base, memory_meta = _format_user_prompt_with_history(message, history)
    if memory_meta.get("turn_count"):
        trace.append(
            {
                "step": "chat_memory",
                "turn_count": memory_meta["turn_count"],
                "truncated": memory_meta.get("truncated", False),
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )

    scoped_docs = [d for d in (document_ids or []) if d]
    graph_available = has_graph_data(scoped_docs or None)
    hits: list[dict[str, Any]] = []
    indexed_total = 0
    retrieval: dict[str, Any] = {
        "l3_hits": [],
        "l4_hits": [],
        "cluster_hits": [],
        "all_hits": [],
        "indexed_total": 0,
        "cluster_ids": [],
    }

    try:
        class_allowed = await allowed_classifications(role_id)
        retrieval = await search_chat_retrieval(
            message.strip(),
            limit=search_limit,
            document_ids=scoped_docs or None,
            history=history,
            fast=True,
            allowed_classifications=class_allowed,
        )
        l3_count = len(retrieval.get("l3_hits") or [])
        l4_count = len(retrieval.get("l4_hits") or [])
        entity_count = len(retrieval.get("entity_hits") or [])
        cluster_count = len(retrieval.get("cluster_hits") or [])
        hits = list(retrieval.get("all_hits") or [])
        hits = _guard_retrieval_hits(hits, message.strip())
        indexed_total = int(retrieval.get("indexed_total") or 0)
        fallback = retrieval.get("fallback")
        fast_retrieval: dict[str, Any] = {
            "step": "fast_retrieval",
            "l3_hit_count": l3_count,
            "l4_hit_count": l4_count,
            "entity_hit_count": entity_count,
            "cluster_hit_count": cluster_count,
            "hit_count": len(hits),
            "indexed_total": indexed_total,
            "raw_query": message.strip(),
            "search_query": retrieval.get("search_query"),
            "fallback": fallback,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }
        if not hits and indexed_total > 0:
            fast_retrieval["warning"] = "поиск пуст — проверьте индекс Qdrant"
        elif not hits and graph_available:
            fast_retrieval["warning"] = "Qdrant пуст — keyword-fallback по графу тоже пуст"
        trace.append(fast_retrieval)
        if fallback and hits:
            trace.append(
                {
                    "step": "graph_keyword_fallback",
                    "hit_count": len(hits),
                    "source": fallback,
                    "fallback": True,
                    "skipped": False,
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }
            )
        elif not hits and graph_available:
            trace.append(
                {
                    "step": "graph_keyword_fallback",
                    "hit_count": 0,
                    "skipped": True,
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }
            )
    except Exception as exc:
        trace.append(
            {
                "step": "fast_retrieval",
                "hit_count": 0,
                "skipped": True,
                "error": str(exc)[:160],
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
        indexed_total = 0
        hits = []

    _append_anomaly_agent_trace(trace, hits, None, t0=t0)

    if indexed_total == 0 and not graph_available and not hits:
        trace.append({"step": "llm_compose", "skipped": True, "elapsed_ms": int((time.perf_counter() - t0) * 1000)})
        timing_ms = int((time.perf_counter() - t0) * 1000)
        return ChatCompleteOut(
            reply=(
                "В карте знаний пока нет проиндексированных документов. "
                "Загрузите PDF в чат и дождитесь индексации."
            ),
            trace=trace,
            graph=None,
            artifacts=[],
            sources=[],
            timing_ms=timing_ms,
            speed_mode="fast",
        )

    qdrant_block = _hits_context_block(hits, limit=search_limit)
    user_prompt = user_prompt_base
    if qdrant_block:
        user_prompt = f"{qdrant_block}\n\n---\n\n{user_prompt}"
        system += (
            f"\n\nНайдено {len(hits)} фрагмент(ов) MKG — ответ строй только по ним; "
            "в «Источники по группам» укажи doc/node из фрагментов."
        )
    elif indexed_total > 0 or graph_available:
        system += (
            "\n\nПоиск MKG (Qdrant + keyword) не вернул фрагментов по запросу. "
            "В «Источники по группам» напиши, что поиск не нашёл совпадений; "
            "не утверждай, что просмотрел фрагменты. Кратко ответь из общих знаний, если уместно."
        )

    try:
        llm = YandexLLMClient.instance()
        reply = await asyncio.wait_for(
            llm.chat(system, user_prompt, temperature=0.25, max_tokens=max_tokens),
            timeout=llm_timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Быстрый ответ: превышен лимит времени LLM (~4 с)") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {exc}") from exc

    text = sanitize_user_facing_text((reply or "").strip())
    if not text:
        raise HTTPException(status_code=502, detail="LLM вернул пустой ответ")

    if comparison_mode:
        text = await _inject_comparison_table(
            message,
            text,
            document_ids=scoped_docs or None,
            hits=hits,
            walked=None,
            trace=trace,
            t0=t0,
        )

    trace.append({"step": "llm_compose", "max_tokens": max_tokens, "elapsed_ms": int((time.perf_counter() - t0) * 1000)})
    timing_ms = int((time.perf_counter() - t0) * 1000)

    return ChatCompleteOut(
        reply=text,
        trace=trace,
        graph=None,
        artifacts=[],
        sources=enrich_search_hits(hits) if hits else [],
        timing_ms=timing_ms,
        speed_mode="compare" if comparison_mode else "fast",
    )


async def run_chat_query(
    message: str,
    role_id: str,
    *,
    history: list[dict[str, str]] | None = None,
    system_prompt: str | None = None,
    include_graph: bool = True,
    include_artifacts: bool = True,
    search_limit: int = 5,
    document_ids: list[str] | None = None,
    speed_mode: str = "full",
    ui_lang: str | None = None,
) -> ChatCompleteOut:
    """Единая точка чата: быстрый RAG, оркестратор L1–L6 (full) или RAG-диалог."""
    comparison_mode = _wants_comparison(message, speed_mode)

    conversational = await run_direct_conversational_reply(
        message,
        role_id,
        history=history,
        speed_mode=speed_mode,
        ui_lang=ui_lang,
    )
    if conversational is not None:
        return conversational

    if speed_mode == "fast":
        return await run_dialog_fast(
            message,
            role_id,
            history=history,
            system_prompt=system_prompt,
            search_limit=min(search_limit, FAST_SEARCH_LIMIT),
            document_ids=document_ids,
            ui_lang=ui_lang,
        )

    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        raise HTTPException(
            status_code=503,
            detail="LLM не настроен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID",
        )

    t0 = time.perf_counter()
    scoped_docs = [d for d in (document_ids or []) if d]
    orchestrated = await _try_orchestrator_chat(
        message,
        role_id,
        history=history,
        include_graph=include_graph,
        search_limit=search_limit,
        document_ids=document_ids,
        t0=t0,
    )
    if orchestrated is not None:
        if comparison_mode:
            walked_dict = None
            if orchestrated.graph and orchestrated.graph.nodes:
                walked_dict = {
                    "nodes": [{"id": n.id, "label": n.label, "props": n.props} for n in orchestrated.graph.nodes],
                    "relationships": [
                        {"type": r.type, "from": r.from_, "to": r.to, "props": r.props}
                        for r in orchestrated.graph.relationships
                    ],
                }
            reply = await _inject_comparison_table(
                message,
                orchestrated.reply,
                document_ids=scoped_docs or None,
                hits=[],
                walked=walked_dict,
                trace=orchestrated.trace,
                t0=t0,
            )
            orchestrated.reply = reply
            orchestrated.speed_mode = "compare"
        return orchestrated

    custom = await get_role_prompt(role_id)
    system = (system_prompt or custom or default_prompt(role_id)).strip()
    if CHAT_OUTPUT_RULES not in system:
        system += f"\n\n{CHAT_OUTPUT_RULES}"
    system, _reply_lang = _apply_reply_language(system, message.strip(), ui_lang)
    if include_artifacts:
        system += (
            "\n\nЕсли уместно показать график или диаграмму, добавь в конец ответа блок:\n"
            "```mkg-artifacts\n"
            '[{"type":"chart","title":"…","chart_type":"bar|line|doughnut",'
            '"labels":["A","B"],"datasets":[{"label":"…","data":[1,2]}]}]\n'
            "```\n"
            "Не добавляй блок, если визуализация не нужна."
        )
    if comparison_mode:
        system += (
            "\n\nПользователь просит сравнение технологий. Дай краткий аналитический ответ; "
            "таблица «## Сравнение технологий» будет добавлена автоматически из графа MKG — "
            "не дублируй markdown-таблицу вручную."
        )

    trace: list[dict[str, Any]] = [
        {"step": "chat_role", "role_id": role_id, "name_ru": role["name_ru"], "pipeline": "dialog", "elapsed_ms": 0},
    ]
    user_prompt_base, memory_meta = _format_user_prompt_with_history(message, history)
    if memory_meta.get("turn_count"):
        trace.append(
            {
                "step": "chat_memory",
                "turn_count": memory_meta["turn_count"],
                "truncated": memory_meta.get("truncated", False),
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
    hits: list[dict[str, Any]] = []
    graph = ContextGraphOut(nodes=[], relationships=[], seed_count=0, document_ids=[])
    retrieval: dict[str, Any] = {
        "l3_hits": [],
        "l4_hits": [],
        "cluster_hits": [],
        "all_hits": [],
        "indexed_total": 0,
        "cluster_ids": [],
    }

    try:
        class_allowed = await allowed_classifications(role_id)
        retrieval = await search_chat_retrieval(
            message.strip(),
            limit=search_limit,
            document_ids=scoped_docs or None,
            history=history,
            allowed_classifications=class_allowed,
        )
        trace.append(
            {
                "step": "qdrant_l3",
                "hit_count": len(retrieval.get("l3_hits") or []),
                "collection": "mkg_chunks",
                "indexed_total": retrieval.get("indexed_total", 0),
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
        trace.append(
            {
                "step": "qdrant_l4_cluster",
                "hit_count": len(retrieval.get("l4_hits") or []),
                "cluster_hit_count": len(retrieval.get("cluster_hits") or []),
                "cluster_ids": retrieval.get("cluster_ids") or [],
                "collection": "mkg_claims",
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
        hits = list(retrieval.get("all_hits") or [])
        hits = _guard_retrieval_hits(hits, message.strip())
    except Exception as exc:
        trace.append(
            {
                "step": "qdrant_l3",
                "hit_count": 0,
                "skipped": True,
                "error": str(exc)[:160],
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
        trace.append(
            {
                "step": "qdrant_l4_cluster",
                "hit_count": 0,
                "cluster_hit_count": 0,
                "skipped": True,
                "error": str(exc)[:160],
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )

    indexed_total = int(retrieval.get("indexed_total") or 0)
    graph_available = has_graph_data(scoped_docs or None)

    if indexed_total == 0 and not graph_available:
        trace.append(
            {
                "step": "graph_traversal",
                "node_count": 0,
                "rel_count": 0,
                "skipped": True,
                "reason": "no_index",
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )
        trace.append({"step": "llm_compose", "skipped": True, "elapsed_ms": int((time.perf_counter() - t0) * 1000)})
        timing_ms = int((time.perf_counter() - t0) * 1000)
        return ChatCompleteOut(
            reply=(
                "В карте знаний пока нет проиндексированных документов. "
                "Загрузите PDF в чат, дождитесь OCR и extraction, затем нажмите «Индексировать» "
                "на вкладке L3 / Qdrant (или дождитесь авто-индексации после построения графа)."
            ),
            trace=trace,
            graph=None,
            artifacts=[],
            sources=[],
            timing_ms=timing_ms,
            speed_mode="full",
        )

    walked: dict[str, Any] = {
        "nodes": [],
        "relationships": [],
        "source": "empty",
        "fallback": False,
        "graph_walk_steps": [],
    }
    if include_graph:
        try:
            walk_steps_collected: list[dict[str, Any]] = []

            def _on_walk_step(step: dict[str, Any]) -> None:
                walk_steps_collected.append(step)
                trace.append(
                    {
                        "step": "graph_walk_step",
                        "order": step.get("order"),
                        "action": step.get("action"),
                        "hop": step.get("hop"),
                        "node_id": step.get("node_id"),
                        "label": step.get("label"),
                        "rel_type": step.get("rel_type"),
                        "from_id": step.get("from_id"),
                        "to_id": step.get("to_id"),
                        "snippet": step.get("snippet"),
                        "source": step.get("source"),
                        "agent_question": step.get("agent_question"),
                        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                    }
                )

            walked = await walk_for_chat(
                hits,
                message.strip(),
                document_ids=scoped_docs or None,
                max_hops=settings.graph_walk_max_hops,
                max_nodes=min(settings.graph_walk_max_nodes, 12),
                max_seeds=settings.graph_walk_max_seeds,
                on_step=_on_walk_step,
            )
            seed_hits = walked.get("seed_hits") or []
            if not hits and seed_hits:
                hits = list(seed_hits)
            if walked.get("nodes"):
                walked = await discover_new_connections(
                    walked,
                    message.strip(),
                    document_ids=scoped_docs or None,
                    max_paths=8,
                )
                trace.append(
                    {
                        "step": "discover_new_connections",
                        "node_count": len(walked.get("nodes") or []),
                        "rel_count": len(walked.get("relationships") or []),
                        "cross_layer": (walked.get("discovery_counts") or {}).get("cross_layer", 0),
                        "cross_document": (walked.get("discovery_counts") or {}).get("cross_document", 0),
                        "total_discoveries": (walked.get("discovery_counts") or {}).get("total", 0),
                        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                    }
                )
            walked = enrich_graph_for_persistence(walked, trace)
            graph = _expanded_to_context_graph(walked)
            trace.append(
                {
                    "step": "graph_traversal",
                    "node_count": len(graph.nodes),
                    "rel_count": len(graph.relationships),
                    "walk_step_count": len(walk_steps_collected),
                    "doc_count": len(graph.document_ids),
                    "seed_count": graph.seed_count,
                    "source": walked.get("source") or "unknown",
                    "fallback": bool(walked.get("fallback")),
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }
            )
            _append_layer_situation_trace(trace, walked, t0=t0)
        except Exception as exc:
            trace.append(
                {
                    "step": "graph_traversal",
                    "node_count": 0,
                    "rel_count": 0,
                    "skipped": True,
                    "error": "graph_build_failed",
                    "error_detail": str(exc)[:160],
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }
            )

    if not any(str(t.get("step") or "") == "l1_agent" for t in trace):
        hit_nodes = [
            {"id": h.get("node_id"), "label": h.get("label")}
            for h in hits
            if h.get("node_id")
        ]
        if hit_nodes:
            _append_layer_situation_trace(trace, {"nodes": hit_nodes, "relationships": []}, t0=t0)

    _append_anomaly_agent_trace(trace, hits, walked if include_graph else None, t0=t0)

    context_parts: list[str] = []
    qdrant_block = _hits_context_block(hits, limit=search_limit + 3)
    if qdrant_block:
        context_parts.append(qdrant_block)
    graph_block = _graph_context_block(graph)
    if graph_block:
        context_parts.append(graph_block)
    context_block = "\n\n---\n\n".join(context_parts)

    user_prompt = user_prompt_base
    if context_block:
        user_prompt = f"{context_block}\n\n---\n\n{user_prompt}"

    try:
        llm = YandexLLMClient.instance()
        reply = await llm.chat(system, user_prompt, temperature=0.35, max_tokens=1024)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {exc}") from exc

    text = sanitize_user_facing_text((reply or "").strip())
    if not text:
        raise HTTPException(status_code=502, detail="LLM вернул пустой ответ")

    artifacts: list[ChatArtifact] = []
    if include_artifacts:
        text, parsed = parse_artifacts_from_reply(text)
        artifacts.extend(parsed)
        for auto in auto_artifacts(message, hits):
            if not any(a.title == auto.title for a in artifacts):
                artifacts.append(auto)

    walked_dict: dict[str, Any] | None = None
    if include_graph and graph.nodes:
        walked_dict = {
            "nodes": [{"id": n.id, "label": n.label, "props": n.props} for n in graph.nodes],
            "relationships": [
                {"type": r.type, "from": r.from_, "to": r.to, "props": r.props}
                for r in graph.relationships
            ],
        }

    if comparison_mode:
        text = await _inject_comparison_table(
            message,
            text,
            document_ids=scoped_docs or None,
            hits=hits,
            walked=walked_dict,
            trace=trace,
            t0=t0,
        )

    trace.append({"step": "llm_compose", "elapsed_ms": int((time.perf_counter() - t0) * 1000)})
    timing_ms = int((time.perf_counter() - t0) * 1000)

    out_speed = "compare" if comparison_mode else "full"
    return ChatCompleteOut(
        reply=text,
        trace=trace,
        graph=graph if include_graph else None,
        artifacts=artifacts if include_artifacts else [],
        sources=enrich_search_hits(hits) if hits else [],
        timing_ms=timing_ms,
        speed_mode=out_speed,
    )
