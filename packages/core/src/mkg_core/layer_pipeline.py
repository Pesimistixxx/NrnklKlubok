"""Статус 6 слоёв L1–L6 и связей для UI пайплайна."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from mkg_core.annotated_md import _LABEL_LAYER, _LAYER_TITLES

L5_LABELS = frozenset({"SecurityRole", "VerificationStatus", "AuditTrail"})

LAYER_ORDER = ("L1", "L2", "L3", "L4", "L5", "L6")

_STEP_RUNNING_LAYERS: dict[str, tuple[str, ...]] = {
    "layer_L3": ("L3",),
    "layer_L5": ("L5",),
    "layer_L2": ("L2",),
    "layer_L6": ("L6",),
    "layer_L2_L6": ("L2", "L6"),
    "layer_L1_L4": ("L1", "L4"),
    "neo4j_load": ("L1", "L2", "L3", "L4", "L5", "L6"),
    "extraction": ("L3", "L5"),
    "cancelling": ("L1", "L2", "L3", "L4", "L5", "L6"),
}


def _running_layers(step: str | None) -> tuple[str, ...]:
    step = step or ""
    if step.startswith("layer_L1_L4"):
        return ("L1", "L4")
    return _STEP_RUNNING_LAYERS.get(step, ())


def _short_node(node: dict[str, Any] | None, node_id: str) -> str:
    if node:
        props = node.get("props") or {}
        for key in ("name", "title", "quote", "text", "value"):
            val = props.get(key)
            if val:
                text = str(val).strip().replace("\n", " ")
                if len(text) > 40:
                    return text[:37] + "…"
                return text
        label = str(node.get("label") or "")
        tail = str(node.get("id") or node_id).split(":", 1)[-1].replace("_", " ")
        return f"{label}: {tail}"[:40] if label else tail[:40]
    tail = node_id.split(":", 1)[-1] if ":" in node_id else node_id
    return tail.replace("_", " ")[:40]


def _node_layer(node: dict[str, Any]) -> str:
    label = str(node.get("label") or "?")
    if label in L5_LABELS:
        return "L5"
    return _LABEL_LAYER.get(label, "L?")


def _infer_layer_status(
    layer_id: str,
    *,
    doc_status: str | None,
    step: str | None,
    node_count: int,
    md_ready: bool,
) -> str:
    status = doc_status or "uploaded"
    step = step or ""
    if status == "extracting":
        running = _running_layers(step)
        if layer_id in running:
            return "running"
        if node_count > 0:
            return "done"
        return "pending"
    if node_count > 0:
        return "done"
    if status == "md_ready" and layer_id == "L3" and md_ready:
        return "partial"
    if status in ("loaded", "md_ready") and node_count == 0:
        return "empty"
    if status == "failed":
        return "failed"
    return "pending"


def build_layer_pipeline(
    *,
    doc_status: str | None,
    step: str | None,
    graph: dict[str, Any] | None,
    md_ready: bool = False,
) -> dict[str, Any]:
    nodes = (graph or {}).get("nodes") or []
    rels = (graph or {}).get("relationships") or []
    node_by_id = {str(n.get("id")): n for n in nodes if n.get("id")}

    layer_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    layer_rels: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for node in nodes:
        layer_nodes[_node_layer(node)].append(node)

    for rel in rels:
        start = str(rel.get("from") or rel.get("from_") or "")
        start_node = node_by_id.get(start)
        layer = _node_layer(start_node) if start_node else "L?"
        layer_rels[layer].append(rel)

    recent: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for rel in reversed(rels):
        start = str(rel.get("from") or rel.get("from_") or "")
        end = str(rel.get("to") or "")
        rtype = str(rel.get("type") or "?")
        key = (start, rtype, end)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        start_node = node_by_id.get(start)
        end_node = node_by_id.get(end)
        recent.append(
            {
                "from_short": _short_node(start_node, start),
                "type": rtype,
                "to_short": _short_node(end_node, end),
                "layer": _node_layer(start_node) if start_node else "L?",
            }
        )
        if len(recent) >= 12:
            break
    recent.reverse()

    layers: list[dict[str, Any]] = []
    for layer_id in LAYER_ORDER:
        ln = layer_nodes.get(layer_id) or []
        lr = layer_rels.get(layer_id) or []
        rel_samples = [
            {
                "from": str(r.get("from") or r.get("from_") or ""),
                "type": str(r.get("type") or "?"),
                "to": str(r.get("to") or ""),
            }
            for r in lr[:5]
        ]
        layers.append(
            {
                "id": layer_id,
                "title": _LAYER_TITLES.get(layer_id, layer_id),
                "status": _infer_layer_status(
                    layer_id,
                    doc_status=doc_status,
                    step=step,
                    node_count=len(ln),
                    md_ready=md_ready,
                ),
                "nodes": len(ln),
                "relationships": len(lr),
                "relationship_samples": rel_samples,
            }
        )

    return {
        "status": doc_status,
        "step": step,
        "layers": layers,
        "total_nodes": len(nodes),
        "total_relationships": len(rels),
        "recent_relationships": recent,
    }
