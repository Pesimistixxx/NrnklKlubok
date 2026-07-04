"""Compact graph payloads for trace steps and live run status."""
from __future__ import annotations

from typing import Any


def graph_snapshot_from_acc(
    acc: dict[str, Any] | None,
    *,
    doc_ids: list[str] | None = None,
    max_nodes: int = 48,
    max_rels: int = 96,
) -> dict[str, Any]:
    """Snapshot accumulated_graph for trace / polling (truncated for payload size)."""
    acc = acc or {}
    nodes = list(acc.get("nodes") or [])[:max_nodes]
    node_ids = {str(n.get("id") or "") for n in nodes if n.get("id")}
    rels: list[dict[str, Any]] = []
    for r in acc.get("relationships") or []:
        if len(rels) >= max_rels:
            break
        frm = str(r.get("from") or r.get("from_") or "")
        to = str(r.get("to") or "")
        if frm in node_ids and to in node_ids:
            rels.append(r)
    docs = set(acc.get("document_ids") or [])
    docs.update(doc_ids or [])
    return {
        "nodes": nodes,
        "relationships": rels,
        "document_ids": sorted(d for d in docs if d),
        "seed_count": len(nodes),
        "new_connections": list(acc.get("new_connections") or [])[:16],
    }


def snapshot_for_trace(acc: dict[str, Any] | None, **kwargs: Any) -> dict[str, Any]:
    """Smaller snapshot embedded in trace steps."""
    return graph_snapshot_from_acc(acc, max_nodes=32, max_rels=64, **kwargs)
