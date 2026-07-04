"""Обход графа Neo4j / локального JSON для контекста AI-поиска."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from mkg_core.config import get_settings
from mkg_core.embeddings import keyword_search
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.neo4j_client import Neo4jClient
from mkg_core.ontology import L4_LABELS
from mkg_core.store import get_repo

log = logging.getLogger(__name__)


def _node_from_neo4j(node_id: str, label: str, props: dict[str, Any]) -> dict[str, Any]:
    clean_props = dict(props or {})
    clean_props.pop("_doc_id", None)
    clean_props.pop("_seed", None)
    return {"id": node_id, "label": label or "?", "props": clean_props}


async def _neo4j_expand(
    seed_ids: list[str],
    *,
    max_hops: int,
    max_nodes: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    if not seed_ids:
        return [], []
    client = Neo4jClient.instance()
    try:
        await client.verify()
    except Exception as exc:
        log.debug("neo4j unavailable for traversal: %s", exc)
        return None

    nodes_by_id: dict[str, dict[str, Any]] = {}
    rels_seen: set[tuple[str, str, str]] = set()
    rels_out: list[dict[str, Any]] = []
    frontier = {sid for sid in seed_ids if sid}
    visited = set(frontier)

    for _hop in range(max(1, max_hops)):
        if not frontier or len(visited) >= max_nodes:
            break
        rows = await client.run(
            """
            UNWIND $ids AS nid
            MATCH (a {id: nid})-[r]-(b)
            WHERE b.id IS NOT NULL
            RETURN a.id AS a_id, labels(a)[0] AS a_label, properties(a) AS a_props,
                   type(r) AS rel_type, properties(r) AS r_props,
                   b.id AS b_id, labels(b)[0] AS b_label, properties(b) AS b_props,
                   startNode(r).id AS from_id, endNode(r).id AS to_id
            LIMIT $limit
            """,
            {"ids": list(frontier), "limit": max_nodes * 6},
        )
        next_frontier: set[str] = set()
        for row in rows:
            for id_key, label_key, props_key in (
                ("a_id", "a_label", "a_props"),
                ("b_id", "b_label", "b_props"),
            ):
                nid = str(row.get(id_key) or "")
                if not nid or nid in nodes_by_id:
                    continue
                nodes_by_id[nid] = _node_from_neo4j(
                    nid, str(row.get(label_key) or ""), dict(row.get(props_key) or {})
                )
            rel_type = str(row.get("rel_type") or "")
            from_id = str(row.get("from_id") or "")
            to_id = str(row.get("to_id") or "")
            if rel_type and from_id and to_id:
                key = (rel_type, from_id, to_id)
                if key not in rels_seen:
                    rels_seen.add(key)
                    rels_out.append(
                        {
                            "type": rel_type,
                            "from": from_id,
                            "to": to_id,
                            "props": dict(row.get("r_props") or {}),
                        }
                    )
            for nid in (str(row.get("b_id") or ""), str(row.get("a_id") or "")):
                if nid and nid not in visited and len(visited) < max_nodes:
                    next_frontier.add(nid)
        visited.update(next_frontier)
        frontier = next_frontier

    for sid in seed_ids:
        if sid and sid not in nodes_by_id:
            seed_rows = await client.run(
                "MATCH (n {id: $id}) RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS props LIMIT 1",
                {"id": sid},
            )
            if seed_rows:
                row = seed_rows[0]
                nodes_by_id[sid] = _node_from_neo4j(
                    sid, str(row.get("label") or ""), dict(row.get("props") or {})
                )

    return list(nodes_by_id.values())[:max_nodes], rels_out[: max_nodes * 3]


def _json_expand(
    seed_ids: set[str],
    graph: dict[str, Any],
    *,
    max_hops: int,
    max_nodes: int,
) -> tuple[set[str], list[dict[str, Any]]]:
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or [] if n.get("id")}
    rels = graph.get("relationships") or []
    expanded = set(seed_ids)
    for _ in range(max(1, max_hops)):
        added: set[str] = set()
        for sid in list(expanded):
            for r in rels:
                f, t = str(r.get("from") or ""), str(r.get("to") or "")
                if f == sid and t in node_by_id:
                    added.add(t)
                elif t == sid and f in node_by_id:
                    added.add(f)
                if len(expanded) + len(added) >= max_nodes:
                    break
            if len(expanded) + len(added) >= max_nodes:
                break
        if not added:
            break
        expanded.update(added)
    expanded = {nid for nid in expanded if nid in node_by_id}
    rels_out = [
        r
        for r in rels
        if str(r.get("from")) in expanded and str(r.get("to")) in expanded
    ]
    return expanded, rels_out


def _cluster_mate_ids_from_graph(graph: dict[str, Any], seed_ids: set[str]) -> set[str]:
    """L4-узлы из того же HDBSCAN-кластера, что и seed-хиты."""
    cluster_ids: set[int] = set()
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or [] if n.get("id")}
    for sid in seed_ids:
        node = node_by_id.get(sid)
        if not node or str(node.get("label") or "") not in L4_LABELS:
            continue
        props = node.get("props") or {}
        cid = props.get("cluster_id", props.get("l4_cluster"))
        try:
            cluster_int = int(cid) if cid is not None else None
        except (TypeError, ValueError):
            cluster_int = None
        if cluster_int is not None and cluster_int >= 0:
            cluster_ids.add(cluster_int)
    if not cluster_ids:
        return set()
    mates: set[str] = set()
    for nid, node in node_by_id.items():
        if str(node.get("label") or "") not in L4_LABELS:
            continue
        props = node.get("props") or {}
        cid = props.get("cluster_id", props.get("l4_cluster"))
        try:
            cluster_int = int(cid) if cid is not None else None
        except (TypeError, ValueError):
            continue
        if cluster_int in cluster_ids:
            mates.add(nid)
    return mates


def _hit_from_neo4j_row(row: dict[str, Any]) -> dict[str, Any]:
    nid = str(row.get("id") or "")
    props = dict(row.get("props") or {})
    text = (
        props.get("name_ru")
        or props.get("raw_text_ru")
        or props.get("quote")
        or props.get("text")
        or props.get("title_ru")
        or ""
    )
    return {
        "node_id": nid,
        "neo4j_node_id": nid,
        "label": str(row.get("label") or ""),
        "layer": str(props.get("layer") or "L?"),
        "score": 0.5,
        "text": str(text)[:500],
        "document_id": str(props.get("document_id") or props.get("_doc_id") or ""),
        "mode": "neo4j_keyword",
        "retrieval_source": "neo4j_keyword",
    }


async def neo4j_keyword_seeds(query: str, *, limit: int = 12) -> list[dict[str, Any]]:
    """Поиск seed-узлов в Neo4j по ключевым словам запроса."""
    q = query.strip().lower()
    if not q:
        return []
    tokens = [t for t in re.split(r"\s+", q) if len(t) >= 2][:4]
    needle = tokens[0] if tokens else q[:48]
    client = Neo4jClient.instance()
    try:
        await client.verify()
    except Exception as exc:
        log.debug("neo4j keyword search unavailable: %s", exc)
        return []

    rows = await client.run(
        """
        MATCH (n)
        WHERE n.id IS NOT NULL
        AND (
          (n.name_ru IS NOT NULL AND toLower(toString(n.name_ru)) CONTAINS $q)
          OR (n.raw_text_ru IS NOT NULL AND toLower(toString(n.raw_text_ru)) CONTAINS $q)
          OR (n.quote IS NOT NULL AND toLower(toString(n.quote)) CONTAINS $q)
          OR (n.text IS NOT NULL AND toLower(toString(n.text)) CONTAINS $q)
          OR (n.title_ru IS NOT NULL AND toLower(toString(n.title_ru)) CONTAINS $q)
        )
        RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS props
        LIMIT $limit
        """,
        {"q": needle, "limit": limit},
    )
    return [_hit_from_neo4j_row(row) for row in rows if row.get("id")]


def keyword_seeds_from_docs(
    query: str,
    document_ids: list[str],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Keyword-fallback по JSON-графам документов чата."""
    repo = get_repo()
    hits: list[dict[str, Any]] = []
    per_doc = max(3, limit // max(len(document_ids), 1))
    for doc_id in document_ids:
        graph = repo.read_graph(doc_id) or {}
        if not graph.get("nodes"):
            continue
        for hit in keyword_search(graph, query, limit=per_doc):
            hit["document_id"] = doc_id
            hit["retrieval_source"] = "graph_keyword"
            hits.append(hit)
        if len(hits) >= limit:
            break
    hits.sort(key=lambda h: -float(h.get("score") or 0))
    return hits[:limit]


def has_graph_data(document_ids: list[str] | None = None) -> bool:
    """Есть ли хотя бы один JSON-граф с узлами."""
    repo = get_repo()
    scoped = [d for d in (document_ids or []) if d]
    if scoped:
        return any((repo.read_graph(doc_id) or {}).get("nodes") for doc_id in scoped)
    items, _total = repo.list(page=1, page_size=200)
    return any((repo.read_graph(item["id"]) or {}).get("nodes") for item in items)


async def expand_for_chat(
    hits: list[dict[str, Any]],
    query: str,
    *,
    document_ids: list[str] | None = None,
    max_hops: int | None = None,
    max_nodes: int = 48,
) -> dict[str, Any]:
    """Обход графа из Qdrant-хитов или fallback: keyword/Neo4j seeds."""
    seeds = list(hits)
    fallback = False
    if not seeds:
        fallback = True
        scoped = [d for d in (document_ids or []) if d]
        if scoped:
            seeds = keyword_seeds_from_docs(query, scoped, limit=max(8, max_nodes // 4))
        if not seeds:
            seeds = await neo4j_keyword_seeds(query, limit=max(8, max_nodes // 4))
    if not seeds:
        return {
            "nodes": [],
            "relationships": [],
            "seed_count": 0,
            "document_ids": [],
            "source": "empty",
            "fallback": fallback,
            "seed_hits": [],
        }
    expanded = await expand_from_search_hits(seeds, max_hops=max_hops, max_nodes=max_nodes)
    expanded["fallback"] = fallback
    expanded["seed_hits"] = seeds
    return expanded


async def expand_from_search_hits(
    hits: list[dict[str, Any]],
    *,
    max_hops: int | None = None,
    max_nodes: int = 48,
) -> dict[str, Any]:
    """Расширяет Qdrant-хиты до подграфа: Neo4j multi-hop, fallback — JSON-графы."""
    settings = get_settings()
    hops = max_hops if max_hops is not None else settings.graph_traversal_max_hops
    if not hits:
        return {"nodes": [], "relationships": [], "seed_count": 0, "document_ids": [], "source": "empty"}

    seeds_by_doc: dict[str, set[str]] = defaultdict(set)
    for hit in hits:
        doc_id = str(hit.get("document_id") or hit.get("doc_id") or "").strip()
        node_id = str(hit.get("neo4j_node_id") or hit.get("node_id") or "").strip()
        if doc_id and node_id:
            seeds_by_doc[doc_id].add(node_id)

    for doc_id, seed_ids in list(seeds_by_doc.items()):
        payload = get_repo().read_graph(doc_id) or {}
        if payload.get("nodes"):
            seeds_by_doc[doc_id].update(_cluster_mate_ids_from_graph(payload, seed_ids))

    all_seed_ids = sorted({nid for ids in seeds_by_doc.values() for nid in ids})
    neo4j_nodes: list[dict[str, Any]] = []
    neo4j_rels: list[dict[str, Any]] = []
    neo4j_result = await _neo4j_expand(all_seed_ids, max_hops=hops, max_nodes=max_nodes)
    used_neo4j = neo4j_result is not None
    if neo4j_result:
        neo4j_nodes, neo4j_rels = neo4j_result

    nodes_out: list[dict[str, Any]] = []
    rels_out: list[dict[str, Any]] = []
    seen_nodes: set[tuple[str, str]] = set()
    seen_rels: set[tuple[str, str, str, str]] = set()
    seed_count = 0

    if used_neo4j and neo4j_nodes:
        neo_by_id = {str(n["id"]): n for n in neo4j_nodes}
        node_to_doc: dict[str, str] = {}
        for hit in hits:
            doc_id = str(hit.get("document_id") or hit.get("doc_id") or "").strip()
            node_id = str(hit.get("neo4j_node_id") or hit.get("node_id") or "").strip()
            if doc_id and node_id:
                node_to_doc[node_id] = doc_id
        for doc_id, seed_ids in seeds_by_doc.items():
            for sid in seed_ids:
                seed_count += 1
        for nid, raw in neo_by_id.items():
            if len(nodes_out) >= max_nodes:
                break
            doc_id = node_to_doc.get(nid) or next(iter(seeds_by_doc.keys()), "")
            key = (doc_id, nid)
            if key in seen_nodes:
                continue
            seen_nodes.add(key)
            props = dict(raw.get("props") or {})
            props["_doc_id"] = doc_id
            if nid in all_seed_ids:
                props["_seed"] = True
            props["neo4j_node_id"] = nid
            nodes_out.append(
                {"id": str(raw["id"]), "label": str(raw.get("label") or ""), "props": props}
            )
        for r in neo4j_rels:
            f, t = str(r.get("from") or ""), str(r.get("to") or "")
            doc_hint = next(iter(seeds_by_doc.keys()), "")
            rel_key = (doc_hint, f, t, str(r.get("type") or ""))
            if rel_key in seen_rels:
                continue
            seen_rels.add(rel_key)
            rels_out.append(r)
        if nodes_out:
            return {
                "nodes": nodes_out[:max_nodes],
                "relationships": rels_out[: max_nodes * 3],
                "seed_count": seed_count,
                "document_ids": sorted(seeds_by_doc.keys()),
                "source": "neo4j",
            }

    for doc_id, seed_ids in seeds_by_doc.items():
        payload = get_repo().read_graph(doc_id) or {}
        if not payload.get("nodes"):
            continue
        graph = dedupe_graph_payload(
            GraphPayload(
                nodes=list(payload.get("nodes") or []),
                relationships=list(payload.get("relationships") or []),
            )
        ).as_dict()
        expanded_ids, doc_rels = _json_expand(seed_ids, graph, max_hops=hops, max_nodes=max_nodes)
        node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or []}
        for sid in seed_ids:
            seed_count += 1
        for nid in expanded_ids:
            key = (doc_id, nid)
            if key in seen_nodes:
                continue
            seen_nodes.add(key)
            raw = dict(node_by_id[nid])
            props = dict(raw.get("props") or {})
            props["_doc_id"] = doc_id
            if nid in seed_ids:
                props["_seed"] = True
            props["neo4j_node_id"] = nid
            nodes_out.append(
                {"id": str(raw["id"]), "label": str(raw.get("label") or ""), "props": props}
            )
        for r in doc_rels:
            f, t = str(r.get("from") or ""), str(r.get("to") or "")
            rel_key = (doc_id, f, t, str(r.get("type") or ""))
            if rel_key in seen_rels:
                continue
            seen_rels.add(rel_key)
            rels_out.append(
                {
                    "type": str(r.get("type") or ""),
                    "from": f,
                    "to": t,
                    "props": dict(r.get("props") or {}),
                }
            )

    return {
        "nodes": nodes_out[:max_nodes],
        "relationships": rels_out[: max_nodes * 3],
        "seed_count": seed_count,
        "document_ids": sorted(seeds_by_doc.keys()),
        "source": "json",
    }
