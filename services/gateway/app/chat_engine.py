"""Общая логика чата: поиск, subgraph, артефакты, LLM."""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from mkg_core.config import get_settings
from mkg_core.embeddings import search_chat_retrieval
from mkg_core.graph_traversal import expand_for_chat, has_graph_data
from mkg_core.llm import YandexLLMClient

from app.collab_db import get_role_prompt
from app.role_prompts import default_prompt
from app.roles import get_role
from app.schemas import ChatArtifact, ChatCompleteOut, ContextGraphOut, GraphNode, GraphRelationship, ChatSourceOut
from app.storage import get_repo

_ARTIFACTS_RE = re.compile(r"```mkg-artifacts\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
_CHART_HINTS = re.compile(
    r"(график|диаграмм|chart|plot|визуализ|сравн|распредел|динамик|тренд|статистик)",
    re.IGNORECASE,
)


def _expanded_to_context_graph(expanded: dict[str, Any]) -> ContextGraphOut:
    if not expanded.get("nodes"):
        return ContextGraphOut(nodes=[], relationships=[], seed_count=0, document_ids=[])
    nodes_out = [
        GraphNode(
            id=str(n["id"]),
            label=str(n.get("label") or ""),
            props=dict(n.get("props") or {}),
        )
        for n in expanded["nodes"]
    ]
    rels_out = [
        GraphRelationship(
            type=str(r.get("type") or ""),
            from_=str(r.get("from") or ""),
            to=str(r.get("to") or ""),
            props=dict(r.get("props") or {}),
        )
        for r in expanded.get("relationships") or []
    ]
    return ContextGraphOut(
        nodes=nodes_out,
        relationships=rels_out,
        seed_count=int(expanded.get("seed_count") or 0),
        document_ids=list(expanded.get("document_ids") or []),
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
    lines = ["Узлы графа MKG (Neo4j обход):"]
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
    if graph.relationships:
        lines.append("\nСвязи графа:")
        for rel in graph.relationships[:18]:
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
            )
        )
    return out


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
) -> ChatCompleteOut:
    """Единая точка: Qdrant L3 + L4 cluster → Neo4j walk → LLM → артефакты."""
    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        raise HTTPException(
            status_code=503,
            detail="LLM не настроен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID",
        )

    custom = await get_role_prompt(role_id)
    system = (system_prompt or custom or default_prompt(role_id)).strip()
    if include_artifacts:
        system += (
            "\n\nЕсли уместно показать график или диаграмму, добавь в конец ответа блок:\n"
            "```mkg-artifacts\n"
            '[{"type":"chart","title":"…","chart_type":"bar|line|doughnut",'
            '"labels":["A","B"],"datasets":[{"label":"…","data":[1,2]}]}]\n'
            "```\n"
            "Не добавляй блок, если визуализация не нужна."
        )

    t0 = time.perf_counter()
    trace: list[dict[str, Any]] = [
        {"step": "chat_role", "role_id": role_id, "name_ru": role["name_ru"], "elapsed_ms": 0},
    ]
    scoped_docs = [d for d in (document_ids or []) if d]
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
        retrieval = await search_chat_retrieval(
            message.strip(),
            limit=search_limit,
            document_ids=scoped_docs or None,
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
        )

    expanded: dict[str, Any] = {"nodes": [], "relationships": [], "source": "empty", "fallback": False}
    if include_graph:
        try:
            expanded = await expand_for_chat(
                hits,
                message.strip(),
                document_ids=scoped_docs or None,
                max_hops=settings.graph_traversal_max_hops,
                max_nodes=48,
            )
            graph = _expanded_to_context_graph(expanded)
            seed_hits = expanded.get("seed_hits") or []
            if not hits and seed_hits:
                hits = list(seed_hits)
            trace.append(
                {
                    "step": "graph_traversal",
                    "node_count": len(graph.nodes),
                    "rel_count": len(graph.relationships),
                    "doc_count": len(graph.document_ids),
                    "seed_count": graph.seed_count,
                    "source": expanded.get("source") or "unknown",
                    "fallback": bool(expanded.get("fallback")),
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }
            )
        except Exception as exc:
            trace.append(
                {
                    "step": "graph_traversal",
                    "node_count": 0,
                    "rel_count": 0,
                    "skipped": True,
                    "error": str(exc)[:160],
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }
            )

    context_parts: list[str] = []
    qdrant_block = _hits_context_block(hits, limit=search_limit + 3)
    if qdrant_block:
        context_parts.append(qdrant_block)
    graph_block = _graph_context_block(graph)
    if graph_block:
        context_parts.append(graph_block)
    context_block = "\n\n---\n\n".join(context_parts)

    lines: list[str] = []
    for turn in (history or [])[-12:]:
        label = "Пользователь" if turn.get("role") == "user" else "Ассистент"
        lines.append(f"{label}: {turn.get('content', '').strip()}")
    lines.append(f"Пользователь: {message.strip()}")
    user_prompt = "\n\n".join(lines)
    if context_block:
        user_prompt = f"{context_block}\n\n---\n\n{user_prompt}"

    try:
        llm = YandexLLMClient.instance()
        reply = await llm.chat(system, user_prompt, temperature=0.35, max_tokens=1536)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {exc}") from exc

    text = (reply or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="LLM вернул пустой ответ")

    artifacts: list[ChatArtifact] = []
    if include_artifacts:
        text, parsed = parse_artifacts_from_reply(text)
        artifacts.extend(parsed)
        for auto in auto_artifacts(message, hits):
            if not any(a.title == auto.title for a in artifacts):
                artifacts.append(auto)

    trace.append({"step": "llm_compose", "elapsed_ms": int((time.perf_counter() - t0) * 1000)})
    timing_ms = int((time.perf_counter() - t0) * 1000)

    return ChatCompleteOut(
        reply=text,
        trace=trace,
        graph=graph if include_graph else None,
        artifacts=artifacts if include_artifacts else [],
        sources=enrich_search_hits(hits) if hits else [],
        timing_ms=timing_ms,
    )
