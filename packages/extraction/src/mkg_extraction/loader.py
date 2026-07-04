"""Загрузка graph payload в Neo4j (идемпотентный MERGE)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mkg_core import Neo4jClient
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload


_SAFE_LABEL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_REL = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SCHEMA_INITIALIZED = False


def _split_statements(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.split(";"):
        lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("//")]
        stmt = "\n".join(lines).strip()
        if stmt:
            out.append(stmt)
    return out


async def ensure_schema_applied() -> bool:
    """Применяет schema.cypher один раз перед первой загрузкой графа."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return True
    candidates = [
        Path.cwd() / "packages" / "graph" / "schema.cypher",
        Path("packages/graph/schema.cypher"),
    ]
    schema_path = next((p for p in candidates if p.exists()), None)
    if schema_path is None:
        return False
    client = Neo4jClient.instance()
    text = schema_path.read_text(encoding="utf-8")
    for stmt in _split_statements(text):
        await client.run_write(stmt)
    _SCHEMA_INITIALIZED = True
    return True


async def load_graph(payload: dict[str, Any]) -> dict[str, int]:
    """Сохраняет payload в Neo4j. Возвращает счетчики загруженных узлов/связей."""
    cleaned = dedupe_graph_payload(
        GraphPayload(
            nodes=list(payload.get("nodes") or []),
            relationships=list(payload.get("relationships") or []),
        )
    )
    payload = cleaned.as_dict()
    client = Neo4jClient.instance()
    await ensure_schema_applied()
    node_count = 0
    rel_count = 0

    for node in payload.get("nodes", []):
        label = node.get("label")
        node_id = node.get("id")
        props = node.get("props", {})
        if not isinstance(label, str) or not _SAFE_LABEL.match(label) or not node_id:
            continue
        cypher = f"""
        MERGE (n:{label} {{id: $id}})
        SET n += $props
        RETURN n.id AS id
        """
        await client.run_write(cypher, {"id": node_id, "props": props})
        node_count += 1

    for rel in payload.get("relationships", []):
        rel_type = rel.get("type")
        start_id = rel.get("from")
        end_id = rel.get("to")
        props = rel.get("props", {})
        if (
            not isinstance(rel_type, str)
            or not _SAFE_REL.match(rel_type)
            or not start_id
            or not end_id
        ):
            continue
        cypher = f"""
        MATCH (a {{id: $from_id}})
        MATCH (b {{id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props
        RETURN type(r) AS type
        """
        rows = await client.run_write(
            cypher,
            {"from_id": start_id, "to_id": end_id, "props": props},
        )
        if rows:
            rel_count += 1

    return {"nodes": node_count, "relationships": rel_count}
