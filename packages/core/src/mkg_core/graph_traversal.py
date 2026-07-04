"""Обход графа Neo4j / локального JSON для контекста AI-поиска."""
from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from mkg_core.config import get_settings
from mkg_core.embeddings import keyword_search
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.neo4j_client import Neo4jClient
from mkg_core.ontology import L4_LABELS
from mkg_core.store import get_repo

log = logging.getLogger(__name__)

StepCallback = Callable[[dict[str, Any]], None]

_CROSS_DOC_ENTITY_LABELS = frozenset({
    "Material", "Process", "Equipment", "ChemicalReagent",
    "Organization", "Person", "Expert", "Facility",
})


def _canonical_entity_key(node: dict[str, Any]) -> str | None:
    label = str(node.get("label") or "")
    if label not in _CROSS_DOC_ENTITY_LABELS:
        return None
    props = dict(node.get("props") or {})
    nid = str(node.get("id") or "")
    base = nid
    if ":" in nid:
        prefix, rest = nid.split(":", 1)
        if len(prefix) >= 8 or prefix.startswith("doc_"):
            base = rest
    name = props.get("name_en") or props.get("name_ru") or props.get("title_ru") or ""
    if name:
        slug = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9]+", "-", str(name).strip().lower())[:48].strip("-")
        return f"{label}:{slug}"
    return f"{label}:{base}"


def _expand_cross_doc_entities(
    nodes_out: list[dict[str, Any]],
    rels_out: list[dict[str, Any]],
    seeds_by_doc: dict[str, set[str]],
    *,
    max_add: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Добавить в контекст обхода сущности с тем же canonical id из других документов."""
    if not nodes_out or not seeds_by_doc:
        return nodes_out, rels_out
    scoped_docs = set(seeds_by_doc.keys())
    keys_in_walk: dict[str, set[str]] = {}
    for n in nodes_out:
        key = _canonical_entity_key(n)
        if not key:
            continue
        doc = str((n.get("props") or {}).get("_doc_id") or "")
        keys_in_walk.setdefault(key, set()).add(doc)
    if not keys_in_walk:
        return nodes_out, rels_out

    repo = get_repo()
    seen = {str(n.get("id") or "") for n in nodes_out if n.get("id")}
    added = 0
    for key, walk_docs in keys_in_walk.items():
        if added >= max_add:
            break
        for doc_id in scoped_docs:
            if added >= max_add:
                break
            graph = repo.read_graph(doc_id) or {}
            for cand in graph.get("nodes") or []:
                if _canonical_entity_key(cand) != key:
                    continue
                cid = str(cand.get("id") or "")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                props = dict(cand.get("props") or {})
                props["_doc_id"] = doc_id
                props["neo4j_node_id"] = cid
                props["_cross_doc_link"] = True
                props["multi_doc_count"] = len(walk_docs | {doc_id})
                nodes_out.append(
                    {"id": cid, "label": str(cand.get("label") or ""), "props": props}
                )
                added += 1
                if added >= max_add:
                    break
    return nodes_out, rels_out


def _node_snippet(props: dict[str, Any], label: str = "") -> str:
    text = (
        props.get("name_ru")
        or props.get("raw_text_ru")
        or props.get("quote")
        or props.get("text")
        or props.get("title_ru")
        or label
        or ""
    )
    return str(text).replace("\n", " ").strip()[:120]


def _agent_question_for_step(
    action: str,
    label: str,
    *,
    rel_type: str = "",
    snippet: str = "",
) -> str:
    """Короткий промежуточный вопрос агента для UI во время обхода графа."""
    name = (snippet or label or "?").strip()
    if len(name) > 50:
        name = name[:47] + "…"
    lbl = label or "узел"
    if action == "seed_load":
        return f"С чего начать: что известно о «{name}»?"
    if rel_type:
        rel_ru = rel_type.replace("_", " ")
        return f"Как «{name}» ({lbl}) связан через {rel_ru}?"
    return f"Что можно узнать о {lbl}: «{name}»?"


def _make_walk_step(
    order: int,
    action: str,
    *,
    hop: int = 0,
    node_id: str = "",
    label: str = "",
    rel_type: str = "",
    from_id: str = "",
    to_id: str = "",
    snippet: str = "",
    doc_id: str = "",
    source: str = "",
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "order": order,
        "action": action,
        "hop": hop,
        "node_id": node_id,
        "label": label,
        "rel_type": rel_type,
        "from_id": from_id,
        "to_id": to_id,
        "snippet": snippet,
        "doc_id": doc_id,
        "source": source,
        "props": props or {},
        "agent_question": _agent_question_for_step(
            action, label, rel_type=rel_type, snippet=snippet
        ),
        "timestamp_ms": int(time.time() * 1000),
    }


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


async def _neo4j_fetch_node(node_id: str) -> dict[str, Any] | None:
    client = Neo4jClient.instance()
    rows = await client.run(
        "MATCH (n {id: $id}) RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS props LIMIT 1",
        {"id": node_id},
    )
    if not rows:
        return None
    row = rows[0]
    return _node_from_neo4j(str(row.get("id") or ""), str(row.get("label") or ""), dict(row.get("props") or {}))


async def _neo4j_neighbors(node_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Один hop от узла — отдельный Cypher-запрос."""
    client = Neo4jClient.instance()
    rows = await client.run(
        """
        MATCH (a {id: $id})-[r]-(b)
        WHERE b.id IS NOT NULL
        RETURN a.id AS a_id, labels(a)[0] AS a_label, properties(a) AS a_props,
               type(r) AS rel_type, properties(r) AS r_props,
               b.id AS b_id, labels(b)[0] AS b_label, properties(b) AS b_props,
               startNode(r).id AS from_id, endNode(r).id AS to_id
        LIMIT $limit
        """,
        {"id": node_id, "limit": limit},
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        b_id = str(row.get("b_id") or "")
        a_id = str(row.get("a_id") or "")
        neighbor_id = b_id if b_id != node_id else a_id
        neighbor_label = str(row.get("b_label") if b_id != node_id else row.get("a_label") or "")
        neighbor_props = dict(row.get("b_props") if b_id != node_id else row.get("a_props") or {})
        out.append(
            {
                "rel_type": str(row.get("rel_type") or ""),
                "from_id": str(row.get("from_id") or ""),
                "to_id": str(row.get("to_id") or ""),
                "neighbor_id": neighbor_id,
                "neighbor_label": neighbor_label,
                "neighbor_props": neighbor_props,
                "rel_props": dict(row.get("r_props") or {}),
            }
        )
    return out


def _json_neighbors(node_id: str, graph: dict[str, Any], *, limit: int = 8) -> list[dict[str, Any]]:
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or [] if n.get("id")}
    if node_id not in node_by_id:
        return []
    out: list[dict[str, Any]] = []
    for r in graph.get("relationships") or []:
        f, t = str(r.get("from") or ""), str(r.get("to") or "")
        rel_type = str(r.get("type") or "")
        if f == node_id and t in node_by_id:
            nb = node_by_id[t]
            out.append(
                {
                    "rel_type": rel_type,
                    "from_id": f,
                    "to_id": t,
                    "neighbor_id": t,
                    "neighbor_label": str(nb.get("label") or ""),
                    "neighbor_props": dict(nb.get("props") or {}),
                    "rel_props": dict(r.get("props") or {}),
                }
            )
        elif t == node_id and f in node_by_id:
            nb = node_by_id[f]
            out.append(
                {
                    "rel_type": rel_type,
                    "from_id": f,
                    "to_id": t,
                    "neighbor_id": f,
                    "neighbor_label": str(nb.get("label") or ""),
                    "neighbor_props": dict(nb.get("props") or {}),
                    "rel_props": dict(r.get("props") or {}),
                }
            )
        if len(out) >= limit:
            break
    return out


def _rank_neighbors(
    neighbors: list[dict[str, Any]],
    *,
    hit_scores: dict[str, float],
    visited: set[str],
) -> list[dict[str, Any]]:
    """Rule-based: предпочитаем Qdrant-хиты и L4-узлы."""
    def score(n: dict[str, Any]) -> float:
        nid = str(n.get("neighbor_id") or "")
        if nid in visited:
            return -1.0
        s = hit_scores.get(nid, 0.0)
        label = str(n.get("neighbor_label") or "")
        if label in L4_LABELS:
            s += 0.3
        return s

    ranked = sorted(neighbors, key=score, reverse=True)
    return [n for n in ranked if str(n.get("neighbor_id") or "") not in visited]


async def _walk_neo4j_bfs(
    seed_ids: list[str],
    *,
    max_hops: int,
    max_nodes: int,
    node_to_doc: dict[str, str],
    hit_scores: dict[str, float],
    on_step: StepCallback | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Последовательный BFS: один Cypher на каждый hop."""
    nodes_by_id: dict[str, dict[str, Any]] = {}
    rels_seen: set[tuple[str, str, str]] = set()
    rels_out: list[dict[str, Any]] = []
    walk_steps: list[dict[str, Any]] = []
    walk_path: list[dict[str, Any]] = []
    order = 0
    visited: set[str] = set()

    def emit(step: dict[str, Any]) -> None:
        walk_steps.append(step)
        if on_step:
            on_step(step)

    for sid in seed_ids:
        if len(visited) >= max_nodes:
            break
        if sid in visited:
            continue
        raw = await _neo4j_fetch_node(sid)
        if not raw:
            continue
        visited.add(sid)
        nodes_by_id[sid] = raw
        doc_id = node_to_doc.get(sid, "")
        order += 1
        step = _make_walk_step(
            order,
            "seed_load",
            hop=0,
            node_id=sid,
            label=str(raw.get("label") or ""),
            snippet=_node_snippet(dict(raw.get("props") or {}), str(raw.get("label") or "")),
            doc_id=doc_id,
            source="neo4j",
        )
        emit(step)
        walk_path.append(
            {
                "node_id": sid,
                "hop": 0,
                "action": "seed_load",
                "agent_question": step.get("agent_question"),
            }
        )

    queue: deque[tuple[str, int]] = deque((sid, 0) for sid in seed_ids if sid in visited)

    while queue and len(visited) < max_nodes:
        current_id, hop = queue.popleft()
        if hop >= max_hops:
            continue
        neighbors = await _neo4j_neighbors(current_id, limit=12)
        for nb in _rank_neighbors(neighbors, hit_scores=hit_scores, visited=visited)[:6]:
            nid = str(nb.get("neighbor_id") or "")
            if not nid or nid in visited:
                continue
            if len(visited) >= max_nodes:
                break
            rel_type = str(nb.get("rel_type") or "")
            from_id = str(nb.get("from_id") or "")
            to_id = str(nb.get("to_id") or "")
            n_label = str(nb.get("neighbor_label") or "")
            n_props = dict(nb.get("neighbor_props") or {})
            visited.add(nid)
            nodes_by_id[nid] = _node_from_neo4j(nid, n_label, n_props)
            rel_key = (rel_type, from_id, to_id)
            if rel_key not in rels_seen:
                rels_seen.add(rel_key)
                rels_out.append(
                    {
                        "type": rel_type,
                        "from": from_id,
                        "to": to_id,
                        "props": dict(nb.get("rel_props") or {}),
                    }
                )
            doc_id = node_to_doc.get(nid) or node_to_doc.get(current_id, "")
            order += 1
            step = _make_walk_step(
                order,
                "traverse",
                hop=hop + 1,
                node_id=nid,
                label=n_label,
                rel_type=rel_type,
                from_id=from_id,
                to_id=to_id,
                snippet=_node_snippet(n_props, n_label),
                doc_id=doc_id,
                source="neo4j",
            )
            emit(step)
            walk_path.append(
                {
                    "node_id": nid,
                    "from_id": current_id,
                    "rel_type": rel_type,
                    "hop": hop + 1,
                    "action": "traverse",
                    "agent_question": step.get("agent_question"),
                }
            )
            queue.append((nid, hop + 1))

    return list(nodes_by_id.values()), rels_out, walk_steps, walk_path


def _walk_json_bfs(
    seed_ids: list[str],
    graph: dict[str, Any],
    doc_id: str,
    *,
    max_hops: int,
    max_nodes: int,
    hit_scores: dict[str, float],
    on_step: StepCallback | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Последовательный BFS по JSON-графу документа."""
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or [] if n.get("id")}
    nodes_out: dict[str, dict[str, Any]] = {}
    rels_seen: set[tuple[str, str, str]] = set()
    rels_out: list[dict[str, Any]] = []
    walk_steps: list[dict[str, Any]] = []
    walk_path: list[dict[str, Any]] = []
    order = 0
    visited: set[str] = set()

    def emit(step: dict[str, Any]) -> None:
        walk_steps.append(step)
        if on_step:
            on_step(step)

    for sid in seed_ids:
        if len(visited) >= max_nodes:
            break
        if sid not in node_by_id or sid in visited:
            continue
        raw = node_by_id[sid]
        visited.add(sid)
        nodes_out[sid] = raw
        props = dict(raw.get("props") or {})
        order += 1
        step = _make_walk_step(
            order,
            "seed_load",
            hop=0,
            node_id=sid,
            label=str(raw.get("label") or ""),
            snippet=_node_snippet(props, str(raw.get("label") or "")),
            doc_id=doc_id,
            source="json",
        )
        emit(step)
        walk_path.append({
            "node_id": sid,
            "hop": 0,
            "action": "seed_load",
            "doc_id": doc_id,
            "agent_question": step.get("agent_question"),
        })

    queue: deque[tuple[str, int]] = deque((sid, 0) for sid in seed_ids if sid in visited)

    while queue and len(visited) < max_nodes:
        current_id, hop = queue.popleft()
        if hop >= max_hops:
            continue
        neighbors = _json_neighbors(current_id, graph, limit=12)
        for nb in _rank_neighbors(neighbors, hit_scores=hit_scores, visited=visited)[:6]:
            nid = str(nb.get("neighbor_id") or "")
            if not nid or nid not in node_by_id or nid in visited:
                continue
            if len(visited) >= max_nodes:
                break
            rel_type = str(nb.get("rel_type") or "")
            from_id = str(nb.get("from_id") or "")
            to_id = str(nb.get("to_id") or "")
            raw = node_by_id[nid]
            n_label = str(raw.get("label") or "")
            n_props = dict(raw.get("props") or {})
            visited.add(nid)
            nodes_out[nid] = raw
            rel_key = (rel_type, from_id, to_id)
            if rel_key not in rels_seen:
                rels_seen.add(rel_key)
                rels_out.append(
                    {
                        "type": rel_type,
                        "from": from_id,
                        "to": to_id,
                        "props": dict(nb.get("rel_props") or {}),
                    }
                )
            order += 1
            step = _make_walk_step(
                order,
                "traverse",
                hop=hop + 1,
                node_id=nid,
                label=n_label,
                rel_type=rel_type,
                from_id=from_id,
                to_id=to_id,
                snippet=_node_snippet(n_props, n_label),
                doc_id=doc_id,
                source="json",
            )
            emit(step)
            walk_path.append(
                {
                    "node_id": nid,
                    "from_id": current_id,
                    "rel_type": rel_type,
                    "hop": hop + 1,
                    "action": "traverse",
                    "doc_id": doc_id,
                    "agent_question": step.get("agent_question"),
                }
            )
            queue.append((nid, hop + 1))

    return list(nodes_out.values()), rels_out, walk_steps, walk_path


async def walk_graph_from_hits(
    hits: list[dict[str, Any]],
    seeds_by_doc: dict[str, set[str]],
    *,
    max_hops: int | None = None,
    max_nodes: int | None = None,
    max_seeds: int | None = None,
    on_step: StepCallback | None = None,
) -> dict[str, Any]:
    """Итеративный обход графа с пошаговым trace."""
    settings = get_settings()
    hops = max_hops if max_hops is not None else settings.graph_walk_max_hops
    nodes_cap = max_nodes if max_nodes is not None else settings.graph_walk_max_nodes
    seeds_cap = max_seeds if max_seeds is not None else settings.graph_walk_max_seeds

    hit_scores: dict[str, float] = {}
    node_to_doc: dict[str, str] = {}
    ordered_seeds: list[str] = []
    seen_seed: set[str] = set()
    for hit in hits:
        doc_id = str(hit.get("document_id") or hit.get("doc_id") or "").strip()
        node_id = str(hit.get("neo4j_node_id") or hit.get("node_id") or "").strip()
        if node_id:
            hit_scores[node_id] = max(hit_scores.get(node_id, 0.0), float(hit.get("score") or 0))
            if doc_id:
                node_to_doc[node_id] = doc_id
            if node_id not in seen_seed:
                seen_seed.add(node_id)
                ordered_seeds.append(node_id)
        if len(ordered_seeds) >= seeds_cap:
            break
    for doc_id, seed_ids in seeds_by_doc.items():
        for sid in sorted(seed_ids):
            if sid not in seen_seed:
                seen_seed.add(sid)
                ordered_seeds.append(sid)
                node_to_doc.setdefault(sid, doc_id)
            if len(ordered_seeds) >= seeds_cap:
                break

    all_seed_ids = ordered_seeds[:seeds_cap]
    if not all_seed_ids:
        return {
            "nodes": [],
            "relationships": [],
            "seed_count": 0,
            "document_ids": [],
            "source": "empty",
            "graph_walk_steps": [],
            "walk_path": [],
        }

    neo4j_available = False
    client = Neo4jClient.instance()
    try:
        await client.verify()
        neo4j_available = True
    except Exception as exc:
        log.debug("neo4j unavailable for walk: %s", exc)

    all_steps: list[dict[str, Any]] = []

    def collect_step(step: dict[str, Any]) -> None:
        all_steps.append(step)
        if on_step:
            on_step(step)

    nodes_out: list[dict[str, Any]] = []
    rels_out: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_rels: set[tuple[str, str, str, str]] = set()
    seed_count = 0

    if neo4j_available:
        neo_nodes, neo_rels, _, _ = await _walk_neo4j_bfs(
            all_seed_ids,
            max_hops=hops,
            max_nodes=nodes_cap,
            node_to_doc=node_to_doc,
            hit_scores=hit_scores,
            on_step=collect_step,
        )
        if neo_nodes:
            for doc_id, seed_ids in seeds_by_doc.items():
                for sid in seed_ids:
                    seed_count += 1
            for raw in neo_nodes:
                nid = str(raw["id"])
                doc_id = node_to_doc.get(nid) or next(iter(seeds_by_doc.keys()), "")
                if nid in seen_nodes:
                    continue
                seen_nodes.add(nid)
                props = dict(raw.get("props") or {})
                props["_doc_id"] = doc_id
                if nid in all_seed_ids:
                    props["_seed"] = True
                props["neo4j_node_id"] = nid
                nodes_out.append(
                    {"id": nid, "label": str(raw.get("label") or ""), "props": props}
                )
            for r in neo_rels:
                f, t = str(r.get("from") or ""), str(r.get("to") or "")
                doc_hint = next(iter(seeds_by_doc.keys()), "")
                rel_key = (doc_hint, f, t, str(r.get("type") or ""))
                if rel_key in seen_rels:
                    continue
                seen_rels.add(rel_key)
                rels_out.append(r)
            nodes_out, rels_out = _expand_cross_doc_entities(
                nodes_out, rels_out, seeds_by_doc, max_add=max(4, nodes_cap // 8)
            )
            return _dedupe_walk_subgraph({
                "nodes": nodes_out[:nodes_cap],
                "relationships": rels_out[: nodes_cap * 3],
                "seed_count": seed_count or len(all_seed_ids),
                "document_ids": sorted(seeds_by_doc.keys()),
                "source": "neo4j",
                "graph_walk_steps": all_steps,
                "walk_path": [
                    {
                        "node_id": s.get("node_id"),
                        "from_id": s.get("from_id"),
                        "rel_type": s.get("rel_type"),
                        "hop": s.get("hop"),
                        "action": s.get("action"),
                    }
                    for s in all_steps
                ],
            })

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
        doc_seeds = [s for s in all_seed_ids if s in seed_ids or s in {str(n.get("id")) for n in graph.get("nodes") or []}]
        if not doc_seeds:
            doc_seeds = sorted(seed_ids)[:seeds_cap]
        json_nodes, json_rels, _, _ = _walk_json_bfs(
            doc_seeds[:seeds_cap],
            graph,
            doc_id,
            max_hops=hops,
            max_nodes=max(nodes_cap - len(nodes_out), 1),
            hit_scores=hit_scores,
            on_step=collect_step,
        )
        for sid in seed_ids:
            seed_count += 1
        node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or []}
        for raw in json_nodes:
            nid = str(raw.get("id") or "")
            if not nid:
                continue
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            props = dict(raw.get("props") or {})
            props["_doc_id"] = doc_id
            if nid in seed_ids:
                props["_seed"] = True
            props["neo4j_node_id"] = nid
            nodes_out.append(
                {"id": nid, "label": str(raw.get("label") or ""), "props": props}
            )
        for r in json_rels:
            f, t = str(r.get("from") or ""), str(r.get("to") or "")
            rel_key = (doc_id, f, t, str(r.get("type") or ""))
            if rel_key in seen_rels:
                continue
            seen_rels.add(rel_key)
            rels_out.append(r)
        if len(nodes_out) >= nodes_cap:
            break

    nodes_out, rels_out = _expand_cross_doc_entities(
        nodes_out, rels_out, seeds_by_doc, max_add=max(4, nodes_cap // 8)
    )
    result = {
        "nodes": nodes_out[:nodes_cap],
        "relationships": rels_out[: nodes_cap * 3],
        "seed_count": seed_count or len(all_seed_ids),
        "document_ids": sorted(seeds_by_doc.keys()),
        "source": "json" if nodes_out else "empty",
        "graph_walk_steps": all_steps,
        "walk_path": [
            {
                "node_id": s.get("node_id"),
                "from_id": s.get("from_id"),
                "rel_type": s.get("rel_type"),
                "hop": s.get("hop"),
                "action": s.get("action"),
                "doc_id": s.get("doc_id"),
                "agent_question": s.get("agent_question"),
            }
            for s in all_steps
        ],
    }
    return _dedupe_walk_subgraph(result)


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


def _annotate_walk_subgraph(result: dict[str, Any]) -> dict[str, Any]:
    """Пометить узлы/рёбра обхода для UI: _visited, _walk_order, _traversed."""
    walk_order: dict[str, int] = {}
    for step in result.get("graph_walk_steps") or []:
        nid = str(step.get("node_id") or "")
        order = int(step.get("order") or 0)
        if nid and nid not in walk_order:
            walk_order[nid] = order
    for n in result.get("nodes") or []:
        props = dict(n.get("props") or {})
        nid = str(n.get("id") or "")
        props["_visited"] = True
        if nid in walk_order:
            props["_walk_order"] = walk_order[nid]
        n["props"] = props
    for r in result.get("relationships") or []:
        props = dict(r.get("props") or {})
        props["_traversed"] = True
        r["props"] = props
    return result


def _dedupe_walk_subgraph(result: dict[str, Any]) -> dict[str, Any]:
    """Убрать дубликаты узлов по id (vis-network / UI не терпят повторов)."""
    payload = dedupe_graph_payload(
        GraphPayload(
            nodes=list(result.get("nodes") or []),
            relationships=list(result.get("relationships") or []),
        )
    )
    out = dict(result)
    out["nodes"] = payload.nodes
    out["relationships"] = payload.relationships
    return out


async def walk_for_chat(
    hits: list[dict[str, Any]],
    query: str,
    *,
    document_ids: list[str] | None = None,
    max_hops: int | None = None,
    max_nodes: int | None = None,
    max_seeds: int | None = None,
    on_step: StepCallback | None = None,
) -> dict[str, Any]:
    """Последовательный обход из Qdrant-хитов — только пройденные узлы и связи (без cluster expansion)."""
    settings = get_settings()
    nodes_cap = max_nodes if max_nodes is not None else settings.graph_walk_max_nodes
    hops = max_hops if max_hops is not None else settings.graph_walk_max_hops
    seeds_cap = max_seeds if max_seeds is not None else settings.graph_walk_max_seeds
    seeds = list(hits)
    fallback = False
    if not seeds:
        fallback = True
        scoped = [d for d in (document_ids or []) if d]
        if scoped:
            seeds = keyword_seeds_from_docs(query, scoped, limit=max(3, seeds_cap))
        if not seeds:
            seeds = await neo4j_keyword_seeds(query, limit=max(3, seeds_cap))
    if not seeds:
        return {
            "nodes": [],
            "relationships": [],
            "seed_count": 0,
            "document_ids": [],
            "source": "empty",
            "fallback": fallback,
            "seed_hits": [],
            "graph_walk_steps": [],
            "walk_path": [],
        }

    seeds_by_doc: dict[str, set[str]] = defaultdict(set)
    repo = get_repo()
    for hit in seeds:
        doc_id = str(hit.get("document_id") or hit.get("doc_id") or "").strip()
        node_id = str(hit.get("neo4j_node_id") or hit.get("node_id") or "").strip()
        if doc_id and node_id:
            seeds_by_doc[doc_id].add(node_id)
        elif node_id:
            for cand in [d for d in (document_ids or []) if d]:
                payload = repo.read_graph(cand) or {}
                if any(str(n.get("id")) == node_id for n in payload.get("nodes") or []):
                    seeds_by_doc[cand].add(node_id)
                    break

    walked = await walk_graph_from_hits(
        seeds,
        dict(seeds_by_doc),
        max_hops=hops,
        max_nodes=nodes_cap,
        max_seeds=seeds_cap,
        on_step=on_step,
    )
    walked["fallback"] = fallback
    walked["seed_hits"] = seeds
    return _annotate_walk_subgraph(_dedupe_walk_subgraph(walked))


async def expand_for_chat(
    hits: list[dict[str, Any]],
    query: str,
    *,
    document_ids: list[str] | None = None,
    max_hops: int | None = None,
    max_nodes: int | None = None,
    on_step: StepCallback | None = None,
) -> dict[str, Any]:
    """Обход графа из Qdrant-хитов или fallback: keyword/Neo4j seeds."""
    settings = get_settings()
    nodes_cap = max_nodes if max_nodes is not None else settings.graph_walk_max_nodes
    hops = max_hops if max_hops is not None else settings.graph_walk_max_hops
    seeds = list(hits)
    fallback = False
    if not seeds:
        fallback = True
        scoped = [d for d in (document_ids or []) if d]
        if scoped:
            seeds = keyword_seeds_from_docs(query, scoped, limit=max(8, nodes_cap // 4))
        if not seeds:
            seeds = await neo4j_keyword_seeds(query, limit=max(8, nodes_cap // 4))
    if not seeds:
        return {
            "nodes": [],
            "relationships": [],
            "seed_count": 0,
            "document_ids": [],
            "source": "empty",
            "fallback": fallback,
            "seed_hits": [],
            "graph_walk_steps": [],
            "walk_path": [],
        }
    expanded = await expand_from_search_hits(
        seeds, max_hops=hops, max_nodes=nodes_cap, on_step=on_step
    )
    expanded["fallback"] = fallback
    expanded["seed_hits"] = seeds
    return expanded


async def expand_from_search_hits(
    hits: list[dict[str, Any]],
    *,
    max_hops: int | None = None,
    max_nodes: int | None = None,
    on_step: StepCallback | None = None,
) -> dict[str, Any]:
    """Расширяет Qdrant-хиты до подграфа итеративным BFS с пошаговым trace."""
    settings = get_settings()
    hops = max_hops if max_hops is not None else settings.graph_walk_max_hops
    nodes_cap = max_nodes if max_nodes is not None else settings.graph_walk_max_nodes
    if not hits:
        return {
            "nodes": [],
            "relationships": [],
            "seed_count": 0,
            "document_ids": [],
            "source": "empty",
            "graph_walk_steps": [],
            "walk_path": [],
        }

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

    if not seeds_by_doc:
        orphan_ids = {
            str(hit.get("neo4j_node_id") or hit.get("node_id") or "").strip()
            for hit in hits
            if hit.get("neo4j_node_id") or hit.get("node_id")
        }
        orphan_ids.discard("")
        if orphan_ids:
            seeds_by_doc[""] = orphan_ids

    return await walk_graph_from_hits(
        hits,
        seeds_by_doc,
        max_hops=hops,
        max_nodes=nodes_cap,
        on_step=on_step,
    )


def _node_layer_label(node: dict[str, Any]) -> str:
    from mkg_core.ontology import LABEL_LAYER

    label = str(node.get("label") or "")
    return LABEL_LAYER.get(label, str((node.get("props") or {}).get("layer") or "L?"))


def _node_slot(node: dict[str, Any]) -> tuple[str, str]:
    props = node.get("props") or {}
    doc_id = str(props.get("_doc_id") or props.get("document_id") or "")
    nid = str(node.get("id") or props.get("neo4j_node_id") or "")
    return doc_id, nid


def _rel_key(doc_id: str, rel: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        doc_id,
        str(rel.get("from") or ""),
        str(rel.get("to") or ""),
        str(rel.get("type") or ""),
    )


def _merge_graph_parts(
    nodes: list[dict[str, Any]],
    rels: list[dict[str, Any]],
    new_nodes: list[dict[str, Any]],
    new_rels: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen_nodes = {_node_slot(n) for n in nodes if _node_slot(n)[1]}
    seen_node_ids = {str(n.get("id") or "") for n in nodes if n.get("id")}
    seen_rels: set[tuple[str, str, str, str]] = set()
    for r in rels:
        doc_hint = str((r.get("props") or {}).get("_doc_id") or "")
        if not doc_hint:
            for n in nodes:
                if str(n.get("id")) in (str(r.get("from")), str(r.get("to"))):
                    doc_hint = str((n.get("props") or {}).get("_doc_id") or "")
                    break
        seen_rels.add(_rel_key(doc_hint, r))

    out_nodes = list(nodes)
    out_rels = list(rels)
    for raw in new_nodes:
        slot = _node_slot(raw)
        nid = str(raw.get("id") or "")
        if not slot[1] or slot in seen_nodes or (nid and nid in seen_node_ids):
            continue
        seen_nodes.add(slot)
        if nid:
            seen_node_ids.add(nid)
        out_nodes.append(raw)
    for raw in new_rels:
        doc_hint = str((raw.get("props") or {}).get("_doc_id") or "")
        key = _rel_key(doc_hint, raw)
        if key in seen_rels:
            continue
        seen_rels.add(key)
        out_rels.append(raw)
    return out_nodes, out_rels


async def discover_cross_layer_edges(
    nodes: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    *,
    document_ids: list[str] | None = None,
    max_edges: int = 24,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Найти рёбра между уже найденными узлами разных слоёв в JSON-графах."""
    if not nodes:
        return nodes, relationships, []
    node_ids_by_doc: dict[str, set[str]] = defaultdict(set)
    layer_by_slot: dict[tuple[str, str], str] = {}
    for n in nodes:
        doc_id, nid = _node_slot(n)
        if not nid:
            continue
        node_ids_by_doc[doc_id or "_global"].add(nid)
        layer_by_slot[(doc_id, nid)] = _node_layer_label(n)

    scoped_docs = [d for d in (document_ids or []) if d]
    if not scoped_docs:
        scoped_docs = sorted({d for d, _ in layer_by_slot.keys() if d})

    repo = get_repo()
    new_nodes: list[dict[str, Any]] = []
    new_rels: list[dict[str, Any]] = []
    discoveries: list[dict[str, Any]] = []
    seen_rels = {_rel_key("", r) for r in relationships}

    for doc_id in scoped_docs:
        graph = repo.read_graph(doc_id) or {}
        if not graph.get("nodes"):
            continue
        local_ids = node_ids_by_doc.get(doc_id) or node_ids_by_doc.get("_global") or set()
        if not local_ids:
            local_ids = {str(n.get("id")) for n in graph.get("nodes") or [] if str(n.get("id")) in {s[1] for s in layer_by_slot}}
        node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or [] if n.get("id")}
        added = 0
        for r in graph.get("relationships") or []:
            if added >= max_edges:
                break
            f, t = str(r.get("from") or ""), str(r.get("to") or "")
            if f not in local_ids or t not in local_ids:
                continue
            rel_key = _rel_key(doc_id, r)
            if rel_key in seen_rels:
                continue
            from_layer = layer_by_slot.get((doc_id, f)) or _node_layer_label(node_by_id.get(f) or {})
            to_layer = layer_by_slot.get((doc_id, t)) or _node_layer_label(node_by_id.get(t) or {})
            if from_layer == to_layer:
                continue
            seen_rels.add(rel_key)
            rel_props = dict(r.get("props") or {})
            rel_props["_cross_layer"] = True
            rel_props["_doc_id"] = doc_id
            new_rels.append(
                {
                    "type": str(r.get("type") or ""),
                    "from": f,
                    "to": t,
                    "props": rel_props,
                }
            )
            for nid in (f, t):
                slot = (doc_id, nid)
                if slot not in layer_by_slot and nid in node_by_id:
                    raw = node_by_id[nid]
                    props = dict(raw.get("props") or {})
                    props["_doc_id"] = doc_id
                    props["neo4j_node_id"] = nid
                    new_nodes.append({"id": nid, "label": str(raw.get("label") or ""), "props": props})
                    layer_by_slot[slot] = _node_layer_label(raw)
            discoveries.append(
                {
                    "kind": "cross_layer",
                    "doc_id": doc_id,
                    "from_id": f,
                    "to_id": t,
                    "rel_type": str(r.get("type") or ""),
                    "from_layer": from_layer,
                    "to_layer": to_layer,
                }
            )
            added += 1

    merged_nodes, merged_rels = _merge_graph_parts(nodes, relationships, new_nodes, new_rels)
    return merged_nodes, merged_rels, discoveries


async def discover_cross_document_links(
    nodes: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    *,
    document_ids: list[str],
    max_add: int = 12,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Сущности с тем же canonical id в других документах + мостовые рёбра."""
    scoped = [d for d in document_ids if d]
    if not nodes or len(scoped) < 2:
        return nodes, relationships, []

    seeds_by_doc: dict[str, set[str]] = defaultdict(set)
    for n in nodes:
        doc_id, nid = _node_slot(n)
        if doc_id and nid:
            seeds_by_doc[doc_id].add(nid)

    expanded_nodes, expanded_rels = _expand_cross_doc_entities(
        list(nodes), list(relationships), dict(seeds_by_doc), max_add=max_add
    )
    discoveries: list[dict[str, Any]] = []
    old_slots = {_node_slot(n) for n in nodes}
    for n in expanded_nodes:
        slot = _node_slot(n)
        if slot in old_slots:
            continue
        props = n.get("props") or {}
        discoveries.append(
            {
                "kind": "cross_document",
                "doc_id": slot[0],
                "node_id": slot[1],
                "label": n.get("label"),
                "entity_key": props.get("name_en") or props.get("name_ru") or slot[1],
            }
        )
        old_slots.add(slot)

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in expanded_nodes:
        key = _canonical_entity_key(n)
        if key:
            by_key[key].append(n)
    bridged: set[tuple[str, str, str]] = set()
    for key, group in by_key.items():
        if len(group) < 2:
            continue
        for i, left in enumerate(group):
            doc_a, nid_a = _node_slot(left)
            for right in group[i + 1 :]:
                doc_b, nid_b = _node_slot(right)
                if doc_a == doc_b:
                    continue
                bridge_key = (min(nid_a, nid_b), max(nid_a, nid_b), key)
                if bridge_key in bridged:
                    continue
                bridged.add(bridge_key)
                expanded_rels.append(
                    {
                        "type": "SHARED_ENTITY",
                        "from": nid_a,
                        "to": nid_b,
                        "props": {"_cross_doc": True, "_doc_id": doc_a, "_doc_id_to": doc_b},
                    }
                )
                discoveries.append(
                    {
                        "kind": "cross_document",
                        "from_id": nid_a,
                        "to_id": nid_b,
                        "doc_id": doc_a,
                        "doc_id_to": doc_b,
                        "rel_type": "SHARED_ENTITY",
                        "entity_key": key,
                    }
                )

    merged_nodes, merged_rels = _merge_graph_parts(nodes, relationships, expanded_nodes, expanded_rels)
    return merged_nodes, merged_rels, discoveries


async def _neo4j_bridge_paths(
    node_ids: list[str],
    existing_rels: list[dict[str, Any]],
    *,
    max_paths: int = 6,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Кратчайшие пути Neo4j между парами найденных узлов без прямой связи."""
    if len(node_ids) < 2:
        return [], [], []
    client = Neo4jClient.instance()
    try:
        await client.verify()
    except Exception:
        return [], [], []

    connected: set[tuple[str, str]] = set()
    for r in existing_rels:
        f, t = str(r.get("from") or ""), str(r.get("to") or "")
        if f and t:
            connected.add((f, t))
            connected.add((t, f))

    new_nodes: list[dict[str, Any]] = []
    new_rels: list[dict[str, Any]] = []
    discoveries: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_rels: set[tuple[str, str, str]] = set()
    pairs_checked = 0

    seeds = node_ids[:8]
    for i, a in enumerate(seeds):
        for b in seeds[i + 1 :]:
            if pairs_checked >= max_paths:
                break
            if (a, b) in connected or (b, a) in connected:
                continue
            pairs_checked += 1
            rows = await client.run(
                """
                MATCH (a {id: $a}), (b {id: $b}), p = shortestPath((a)-[*..4]-(b))
                RETURN p LIMIT 1
                """,
                {"a": a, "b": b},
            )
            if not rows:
                continue
            path_rows = await client.run(
                """
                MATCH (a {id: $a}), (b {id: $b}), p = shortestPath((a)-[*..4]-(b))
                UNWIND relationships(p) AS r
                RETURN startNode(r).id AS from_id, endNode(r).id AS to_id, type(r) AS rel_type,
                       labels(startNode(r))[0] AS from_label, properties(startNode(r)) AS from_props,
                       labels(endNode(r))[0] AS to_label, properties(endNode(r)) AS to_props
                """,
                {"a": a, "b": b},
            )
            for row in path_rows:
                f_id = str(row.get("from_id") or "")
                t_id = str(row.get("to_id") or "")
                rel_type = str(row.get("rel_type") or "")
                rel_key = (rel_type, f_id, t_id)
                if rel_key in seen_rels:
                    continue
                seen_rels.add(rel_key)
                new_rels.append(
                    {
                        "type": rel_type,
                        "from": f_id,
                        "to": t_id,
                        "props": {"_discovered_path": True},
                    }
                )
                for nid, label, props in (
                    (f_id, row.get("from_label"), row.get("from_props")),
                    (t_id, row.get("to_label"), row.get("to_props")),
                ):
                    if nid and nid not in seen_nodes:
                        seen_nodes.add(nid)
                        new_nodes.append(
                            _node_from_neo4j(nid, str(label or ""), dict(props or {}))
                        )
            discoveries.append(
                {
                    "kind": "neo4j_path",
                    "from_id": a,
                    "to_id": b,
                    "hop_count": len(path_rows),
                }
            )

    return new_nodes, new_rels, discoveries


async def discover_new_connections(
    subgraph: dict[str, Any],
    query: str,
    *,
    document_ids: list[str] | None = None,
    max_paths: int = 8,
) -> dict[str, Any]:
    """Расширить подграф: cross-layer, cross-document, Neo4j paths между найденными узлами."""
    nodes = list(subgraph.get("nodes") or [])
    rels = list(subgraph.get("relationships") or [])
    doc_ids = [d for d in (document_ids or subgraph.get("document_ids") or []) if d]
    if not doc_ids:
        doc_ids = sorted({str((n.get("props") or {}).get("_doc_id") or "") for n in nodes if (n.get("props") or {}).get("_doc_id")})

    all_discoveries: list[dict[str, Any]] = []

    nodes, rels, cross_layer = await discover_cross_layer_edges(
        nodes, rels, document_ids=doc_ids or None, max_edges=max(12, max_paths * 2)
    )
    all_discoveries.extend(cross_layer)

    if len(doc_ids) >= 2:
        nodes, rels, cross_doc = await discover_cross_document_links(
            nodes, rels, document_ids=doc_ids, max_add=max(8, max_paths)
        )
        all_discoveries.extend(cross_doc)

    node_ids = [str(n.get("id") or "") for n in nodes if n.get("id")]
    bridge_nodes, bridge_rels, bridge_disc = await _neo4j_bridge_paths(
        node_ids, rels, max_paths=max_paths
    )
    nodes, rels = _merge_graph_parts(nodes, rels, bridge_nodes, bridge_rels)
    all_discoveries.extend(bridge_disc)

    for r in rels:
        props = dict(r.get("props") or {})
        if props.get("_cross_layer") or props.get("_cross_doc") or props.get("_discovered_path"):
            props["_traversed"] = True
            r["props"] = props

    result = dict(subgraph)
    result["nodes"] = nodes
    result["relationships"] = rels
    result["document_ids"] = doc_ids
    result["new_connections"] = all_discoveries
    result["discovery_counts"] = {
        "cross_layer": len(cross_layer),
        "cross_document": sum(1 for d in all_discoveries if d.get("kind") == "cross_document"),
        "neo4j_paths": len(bridge_disc),
        "total": len(all_discoveries),
    }
    result["query"] = query
    return _annotate_walk_subgraph(_dedupe_walk_subgraph(result))
