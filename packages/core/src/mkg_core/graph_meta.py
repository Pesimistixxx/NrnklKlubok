"""Compact graph payloads for chat message meta persistence."""
from __future__ import annotations

import json
from typing import Any

_PROP_TEXT_KEYS = (
    "raw_text_ru",
    "quote",
    "text",
    "name_ru",
    "title_ru",
    "description",
    "snippet",
    "summary",
    "content",
)
_WALK_STEP_KEYS = (
    "order",
    "action",
    "hop",
    "node_id",
    "label",
    "rel_type",
    "from_id",
    "to_id",
    "snippet",
    "source",
    "agent_question",
)


def _trim_text(value: Any, max_len: int) -> str:
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _trim_node_props(props: dict[str, Any] | None, *, max_prop_len: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in (props or {}).items():
        if isinstance(val, str) and key in _PROP_TEXT_KEYS:
            out[key] = _trim_text(val, max_prop_len)
        elif isinstance(val, (str, int, float, bool)) or val is None:
            out[key] = val
        elif isinstance(val, list) and all(isinstance(x, (str, int, float, bool)) for x in val[:8]):
            out[key] = val[:8]
    return out


def walk_steps_from_trace(trace: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for item in trace or []:
        if str(item.get("step") or "") != "graph_walk_step":
            continue
        step = {k: item[k] for k in _WALK_STEP_KEYS if k in item}
        if step.get("node_id") or step.get("label"):
            steps.append(step)
    return steps


def walk_path_from_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path: list[dict[str, Any]] = []
    for step in steps:
        node_id = step.get("node_id")
        if not node_id:
            continue
        path.append(
            {
                "node_id": node_id,
                "from_id": step.get("from_id"),
                "to_id": step.get("to_id"),
                "rel_type": step.get("rel_type"),
                "label": step.get("label"),
            }
        )
    return path


def synthesize_walk_from_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = list(graph.get("nodes") or [])
    rels = list(graph.get("relationships") or [])
    if not nodes:
        return []
    node_by_id = {str(n.get("id") or ""): n for n in nodes if n.get("id")}
    steps: list[dict[str, Any]] = []
    order = 1
    visited: set[str] = set()

    def append_step(node: dict[str, Any], *, action: str, rel_type: str = "", from_id: str = "") -> None:
        nonlocal order
        nid = str(node.get("id") or "")
        if not nid or nid in visited:
            return
        visited.add(nid)
        props = node.get("props") if isinstance(node.get("props"), dict) else {}
        snippet = (
            props.get("quote")
            or props.get("raw_text_ru")
            or props.get("name_ru")
            or props.get("text")
            or ""
        )
        steps.append(
            {
                "order": order,
                "action": action,
                "hop": max(0, order - 1),
                "node_id": nid,
                "label": node.get("label") or props.get("name_ru") or nid,
                "rel_type": rel_type or None,
                "from_id": from_id or None,
                "to_id": nid,
                "snippet": _trim_text(snippet, 240),
                "source": "persisted",
            }
        )
        order += 1

    seed = next((n for n in nodes if (n.get("props") or {}).get("_seed")), nodes[0])
    append_step(seed, action="seed_load")
    cursor = str(seed.get("id") or "")
    for _ in range(len(nodes) + 2):
        nxt_rel = next(
            (r for r in rels if str(r.get("from") or "") == cursor and str(r.get("to") or "") not in visited),
            None,
        )
        if not nxt_rel:
            break
        to_id = str(nxt_rel.get("to") or "")
        target = node_by_id.get(to_id)
        if not target:
            break
        append_step(
            target,
            action="traverse",
            rel_type=str(nxt_rel.get("type") or ""),
            from_id=cursor,
        )
        cursor = to_id
    for node in nodes:
        append_step(node, action="traverse")
    return steps[:48]


def graph_from_layer_results(layer_results: list[dict[str, Any]] | None) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_rels: set[tuple[str, str, str]] = set()
    for lr in layer_results or []:
        for node in lr.get("nodes_found") or []:
            nid = str(node.get("id") or "")
            if nid and nid not in seen_nodes:
                seen_nodes.add(nid)
                nodes.append(node)
        for rel in lr.get("edges_found") or []:
            key = (
                str(rel.get("from") or ""),
                str(rel.get("type") or ""),
                str(rel.get("to") or ""),
            )
            if key[0] and key[1] and key[2] and key not in seen_rels:
                seen_rels.add(key)
                relationships.append(rel)
    return {"nodes": nodes, "relationships": relationships}


def enrich_graph_for_persistence(
    graph: dict[str, Any] | None,
    trace: list[dict[str, Any]] | None = None,
    *,
    layer_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base = dict(graph or {})
    if not (base.get("nodes") or base.get("relationships")) and layer_results:
        base = graph_from_layer_results(layer_results)
    steps = list(base.get("graph_walk_steps") or [])
    if not steps:
        steps = walk_steps_from_trace(trace)
    if not steps and base.get("nodes"):
        steps = synthesize_walk_from_graph(base)
    if steps:
        base["graph_walk_steps"] = steps
    if not base.get("walk_path") and steps:
        base["walk_path"] = walk_path_from_steps(steps)
    base.setdefault("seed_count", len(base.get("nodes") or []))
    base.setdefault("document_ids", [])
    return base


def compact_graph_for_meta(
    graph: dict[str, Any] | None,
    *,
    max_nodes: int = 64,
    max_rels: int = 128,
    max_walk_steps: int = 48,
    max_prop_len: int = 400,
) -> dict[str, Any] | None:
    if not graph:
        return None
    nodes_in = list(graph.get("nodes") or [])[:max_nodes]
    node_ids = {str(n.get("id") or "") for n in nodes_in if n.get("id")}
    nodes_out: list[dict[str, Any]] = []
    for node in nodes_in:
        nid = str(node.get("id") or "")
        if not nid:
            continue
        nodes_out.append(
            {
                "id": nid,
                "label": _trim_text(node.get("label") or "?", 160),
                "props": _trim_node_props(
                    node.get("props") if isinstance(node.get("props"), dict) else {},
                    max_prop_len=max_prop_len,
                ),
            }
        )
    rels_out: list[dict[str, Any]] = []
    for rel in graph.get("relationships") or []:
        if len(rels_out) >= max_rels:
            break
        frm = str(rel.get("from") or rel.get("from_") or "")
        to = str(rel.get("to") or "")
        if frm not in node_ids or to not in node_ids:
            continue
        rels_out.append(
            {
                "type": _trim_text(rel.get("type") or "", 80),
                "from": frm,
                "to": to,
                "props": _trim_node_props(
                    rel.get("props") if isinstance(rel.get("props"), dict) else {},
                    max_prop_len=max_prop_len,
                ),
            }
        )
    walk_steps = []
    for step in graph.get("graph_walk_steps") or []:
        if len(walk_steps) >= max_walk_steps:
            break
        item = {k: step[k] for k in _WALK_STEP_KEYS if k in step}
        if item.get("snippet"):
            item["snippet"] = _trim_text(item["snippet"], max_prop_len)
        if item.get("agent_question"):
            item["agent_question"] = _trim_text(item["agent_question"], max_prop_len)
        walk_steps.append(item)
    walk_path = walk_path_from_steps(walk_steps) if walk_steps else list(graph.get("walk_path") or [])[:max_walk_steps]
    if not nodes_out and not rels_out and not walk_steps:
        return None
    return {
        "nodes": nodes_out,
        "relationships": rels_out,
        "graph_walk_steps": walk_steps,
        "walk_path": walk_path,
        "seed_count": int(graph.get("seed_count") or len(nodes_out)),
        "document_ids": list(graph.get("document_ids") or [])[:24],
    }


def compact_message_meta(meta: dict[str, Any] | None, *, max_json_bytes: int = 512_000) -> dict[str, Any]:
    """Trim graph/trace payload before JSONB insert (Postgres JSONB has no hard row cap)."""
    out = dict(meta or {})
    trace = list(out.get("trace") or [])
    layer_results = out.get("layer_results")
    graph = out.get("graph")
    if graph is not None or trace or layer_results:
        enriched = enrich_graph_for_persistence(graph, trace, layer_results=layer_results)
        compact = compact_graph_for_meta(enriched)
        if compact:
            out["graph"] = compact
        elif "graph" in out and not compact:
            out.pop("graph", None)
    if len(trace) > 120:
        out["trace"] = trace[:120]
    if isinstance(layer_results, list) and len(layer_results) > 12:
        out["layer_results"] = layer_results[:12]
    encoded = json.dumps(out, ensure_ascii=False)
    if len(encoded.encode("utf-8")) <= max_json_bytes:
        return out
    if out.get("graph"):
        out["graph"] = compact_graph_for_meta(
            out["graph"],
            max_nodes=32,
            max_rels=64,
            max_walk_steps=24,
            max_prop_len=240,
        )
    encoded = json.dumps(out, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > max_json_bytes and out.get("trace"):
        out["trace"] = out["trace"][:60]
    return out
