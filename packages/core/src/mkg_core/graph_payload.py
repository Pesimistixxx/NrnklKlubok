"""Graph payload и дедупликация узлов/связей (общий для gateway и worker)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GraphPayload:
    nodes: list[dict[str, Any]]
    relationships: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "relationships": self.relationships}


def dedupe_graph_payload(payload: GraphPayload) -> GraphPayload:
    """Убирает дубликаты узлов по id и дубликаты связей (from, type, to)."""
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in payload.nodes:
        nid = str(node.get("id") or "").strip()
        if not nid:
            continue
        label = str(node.get("label") or "?")
        props = node.get("props") if isinstance(node.get("props"), dict) else {}
        if nid in nodes_by_id:
            existing = nodes_by_id[nid]
            merged = dict(existing.get("props") or {})
            merged.update(props)
            existing["props"] = merged
        else:
            nodes_by_id[nid] = {"id": nid, "label": label, "props": dict(props)}

    valid_ids = set(nodes_by_id)
    seen_rels: set[tuple[str, str, str]] = set()
    rels: list[dict[str, Any]] = []
    for rel in payload.relationships:
        start = str(rel.get("from") or "")
        rtype = str(rel.get("type") or "")
        end = str(rel.get("to") or "")
        if not start or not rtype or not end:
            continue
        key = (start, rtype, end)
        if key in seen_rels:
            continue
        if start not in valid_ids or end not in valid_ids:
            continue
        seen_rels.add(key)
        props = rel.get("props") if isinstance(rel.get("props"), dict) else {}
        rels.append({"type": rtype, "from": start, "to": end, "props": props})

    return GraphPayload(nodes=list(nodes_by_id.values()), relationships=rels)
