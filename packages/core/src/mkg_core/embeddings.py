"""Индексация и семантический поиск по TextParagraph / Claim в Qdrant.

Клиент эмбеддингов: ``YandexLLMClient.embed()`` (text-search-doc / text-search-query).
Коллекции Qdrant: ``mkg_chunks`` (L3 абзацы), ``mkg_claims`` (L4 утверждения).

Пайплайн extraction пока не пишет в Qdrant автоматически — индексация по запросу
(POST /agents/documents/{id}/search с index_if_missing=true) или явный вызов
``index_document_graph``.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Literal

from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, PointStruct

from mkg_core.annotated_md import _LABEL_LAYER
from mkg_core.config import get_settings
from mkg_core.llm import YandexLLMClient
from mkg_core.ontology import L4_LABELS
from mkg_core.qdrant import QdrantClientSingleton
from mkg_core.store import get_repo

log = logging.getLogger(__name__)

SearchMode = Literal["auto", "semantic", "keyword"]

_TEXT_KEYS = ("raw_text_ru", "quote", "text", "name_ru", "title_ru", "value", "name")


def _point_id(node_id: str) -> int:
    return int(hashlib.md5(node_id.encode()).hexdigest()[:15], 16)


def _node_text(node: dict[str, Any]) -> str:
    props = node.get("props") or {}
    for key in _TEXT_KEYS:
        val = props.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _node_layer(node: dict[str, Any]) -> str:
    label = str(node.get("label") or "?")
    if label in {"SecurityRole", "VerificationStatus", "AuditTrail"}:
        return "L5"
    return _LABEL_LAYER.get(label, "L?")


def _collection_for_label(label: str) -> str:
    settings = get_settings()
    if label in L4_LABELS:
        return settings.qdrant_collection_claims
    return settings.qdrant_collection_chunks


def _indexable_labels() -> frozenset[str]:
    return frozenset({"TextParagraph"}) | L4_LABELS


def _search_hit(
    payload: dict[str, Any],
    *,
    score: float,
    mode: str,
    retrieval_factors: list[str] | None = None,
) -> dict[str, Any]:
    node_id = str(payload.get("neo4j_node_id") or payload.get("node_id") or "")
    hit: dict[str, Any] = {
        "node_id": node_id,
        "neo4j_node_id": node_id,
        "label": str(payload.get("label") or ""),
        "layer": str(payload.get("layer") or "L?"),
        "score": score,
        "text": str(payload.get("text") or "")[:500],
        "document_id": str(payload.get("document_id") or ""),
        "cluster_id": payload.get("cluster_id"),
        "is_anomaly": payload.get("is_anomaly"),
        "anomaly_score": payload.get("anomaly_score"),
        "props": {},
        "mode": mode,
    }
    if retrieval_factors:
        hit["retrieval_factors"] = list(retrieval_factors)
    return hit


def _hit_key(hit: dict[str, Any]) -> tuple[str, str]:
    return (
        str(hit.get("document_id") or ""),
        str(hit.get("node_id") or hit.get("neo4j_node_id") or ""),
    )


def _merge_hit(existing: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        return dict(new)
    merged = dict(existing)
    merged["score"] = max(float(existing.get("score") or 0), float(new.get("score") or 0))
    factors = set(existing.get("retrieval_factors") or [])
    factors.update(new.get("retrieval_factors") or [])
    if factors:
        merged["retrieval_factors"] = sorted(factors)
    return merged


def _graph_hit_from_node(node: dict[str, Any], *, document_id: str, score: float) -> dict[str, Any]:
    props = node.get("props") or {}
    payload = {
        "document_id": document_id,
        "node_id": str(node.get("id") or ""),
        "neo4j_node_id": str(node.get("id") or ""),
        "label": str(node.get("label") or ""),
        "layer": _node_layer(node),
        "text": _node_text(node) or str(props.get("text") or ""),
        "cluster_id": props.get("cluster_id"),
        "is_anomaly": props.get("is_anomaly"),
        "anomaly_score": props.get("anomaly_score"),
    }
    return _search_hit(
        payload,
        score=score,
        mode="graph_bridge",
        retrieval_factors=["l4_graph_bridge"],
    )


def _linked_l4_from_graph(graph: dict[str, Any], l3_ids: set[str]) -> list[dict[str, Any]]:
    """L4-узлы, связанные с L3 TextParagraph через связи графа."""
    if not l3_ids:
        return []
    nodes = {str(n.get("id")): n for n in graph.get("nodes") or [] if n.get("id")}
    l4_labels = set(L4_LABELS)
    found: dict[str, dict[str, Any]] = {}

    def _add_l4(nid: str) -> None:
        if nid not in nodes:
            return
        n = nodes[nid]
        if str(n.get("label")) not in l4_labels:
            return
        props = n.get("props") or {}
        found[nid] = {
            "node_id": nid,
            "label": str(n.get("label") or ""),
            "cluster_id": props.get("cluster_id"),
            "is_anomaly": props.get("is_anomaly"),
            "anomaly_score": props.get("anomaly_score"),
            "text": _node_text(n),
        }

    for rel in graph.get("relationships") or []:
        f, t = str(rel.get("from") or ""), str(rel.get("to") or "")
        for l3_id in l3_ids:
            if f == l3_id:
                _add_l4(t)
            elif t == l3_id:
                _add_l4(f)
    return list(found.values())


async def ensure_qdrant_collections() -> None:
    await QdrantClientSingleton.instance().ensure_collections()


async def count_indexed_points(*, document_id: str | None = None) -> dict[str, int]:
    """Статистика точек в коллекциях (опционально по document_id)."""
    settings = get_settings()
    qdrant = QdrantClientSingleton.instance().client
    out: dict[str, int] = {}
    filt: Filter | None = None
    if document_id:
        filt = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    for name in (settings.qdrant_collection_chunks, settings.qdrant_collection_claims):
        try:
            if filt:
                result = await qdrant.count(collection_name=name, count_filter=filt)
                out[name] = int(result.count)
            else:
                info = await qdrant.get_collection(name)
                out[name] = int(info.points_count or 0)
        except Exception as exc:
            log.warning("qdrant count %s: %s", name, exc)
            out[name] = 0
    return out


def _markdown_chunks(markdown: str, *, max_len: int = 1200) -> list[str]:
    """Разбить Markdown на абзацы для индексации в Qdrant (режим answers_only)."""
    text = (markdown or "").strip()
    if not text:
        return []
    parts = re.split(r"\n\s*\n+", text)
    chunks: list[str] = []
    buf = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(buf) + len(part) + 2 <= max_len:
            buf = f"{buf}\n\n{part}".strip() if buf else part
        else:
            if buf:
                chunks.append(buf)
            if len(part) <= max_len:
                buf = part
            else:
                for i in range(0, len(part), max_len):
                    chunks.append(part[i : i + max_len])
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


async def index_document_markdown(document_id: str, markdown: str | None = None) -> dict[str, int]:
    """Индексация чанков Markdown в Qdrant без графа (режим «только для ответов»)."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return {"indexed": 0, "skipped": 0, "error": "YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы"}

    md = markdown if markdown is not None else (get_repo().read_markdown(document_id) or "")
    chunks = _markdown_chunks(md)
    if not chunks:
        return {"indexed": 0, "skipped": 0, "error": "markdown пуст"}

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    qdrant = QdrantClientSingleton.instance().client
    repo = get_repo()
    collection = settings.qdrant_collection_chunks
    points: list[PointStruct] = []
    indexed = 0
    skipped = 0

    for i, text in enumerate(chunks):
        node_id = f"{document_id}:md_chunk:{i}"
        try:
            vector = await llm.embed(text[:8000], kind="doc")
        except Exception as exc:
            log.warning("embed failed chunk=%s: %s", node_id, exc)
            skipped += 1
            continue
        points.append(
            PointStruct(
                id=_point_id(node_id),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "node_id": node_id,
                    "neo4j_node_id": node_id,
                    "label": "TextParagraph",
                    "layer": "L3",
                    "text": text[:2000],
                    "md_file": repo.markdown_relative_path(document_id),
                    "source": "markdown",
                },
            )
        )
        indexed += 1

    batch_size = 32
    for i in range(0, len(points), batch_size):
        await qdrant.upsert(collection_name=collection, points=points[i : i + batch_size])

    return {"indexed": indexed, "skipped": skipped}


async def index_document_graph(document_id: str, graph: dict[str, Any] | None) -> dict[str, int]:
    """Эмбеддит TextParagraph и Claim из графа и upsert в Qdrant."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return {"indexed": 0, "skipped": 0, "error": "YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы"}

    nodes = (graph or {}).get("nodes") or []
    indexable = [n for n in nodes if str(n.get("label")) in _indexable_labels() and _node_text(n)]
    if not indexable:
        return {"indexed": 0, "skipped": 0}

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    qdrant = QdrantClientSingleton.instance().client

    by_collection: dict[str, list[PointStruct]] = {}
    indexed = 0
    skipped = 0

    for node in indexable:
        label = str(node.get("label"))
        node_id = str(node.get("id") or "")
        text = _node_text(node)
        if not node_id or not text:
            skipped += 1
            continue
        try:
            vector = await llm.embed(text[:8000], kind="doc")
        except Exception as exc:
            log.warning("embed failed node=%s: %s", node_id, exc)
            skipped += 1
            continue
        collection = _collection_for_label(label)
        repo = get_repo()
        point = PointStruct(
            id=_point_id(node_id),
            vector=vector,
            payload={
                "document_id": document_id,
                "node_id": node_id,
                "neo4j_node_id": node_id,
                "label": label,
                "layer": _node_layer(node),
                "text": text[:2000],
                "md_file": repo.markdown_relative_path(document_id),
            },
        )
        by_collection.setdefault(collection, []).append(point)
        indexed += 1

    for collection, points in by_collection.items():
        batch_size = 32
        for i in range(0, len(points), batch_size):
            await qdrant.upsert(collection_name=collection, points=points[i : i + batch_size])

    return {"indexed": indexed, "skipped": skipped}


async def list_indexed_points(
    document_id: str | None = None,
    *,
    collection: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Scroll Qdrant — точки документа или все (payload без вектора)."""
    settings = get_settings()
    qdrant = QdrantClientSingleton.instance().client
    names = [collection] if collection else [
        settings.qdrant_collection_chunks,
        settings.qdrant_collection_claims,
    ]
    filt: Filter | None = None
    if document_id is not None:
        filt = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    out: list[dict[str, Any]] = []
    for name in names:
        if name not in (settings.qdrant_collection_chunks, settings.qdrant_collection_claims):
            continue
        try:
            offset = None
            while len(out) < limit:
                batch_limit = min(64, limit - len(out))
                records, offset = await qdrant.scroll(
                    collection_name=name,
                    scroll_filter=filt,
                    limit=batch_limit,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for rec in records:
                    payload = dict(rec.payload or {})
                    point: dict[str, Any] = {
                        "collection": name,
                        "point_id": str(rec.id),
                        "node_id": payload.get("node_id"),
                        "neo4j_node_id": payload.get("neo4j_node_id") or payload.get("node_id"),
                        "label": payload.get("label"),
                        "layer": payload.get("layer"),
                        "text": (payload.get("text") or "")[:300],
                        "cluster_id": payload.get("cluster_id"),
                        "is_anomaly": payload.get("is_anomaly"),
                        "anomaly_score": payload.get("anomaly_score"),
                    }
                    if document_id is None:
                        point["document_id"] = payload.get("document_id")
                    out.append(point)
                if offset is None or not records:
                    break
        except Exception as exc:
            log.warning("qdrant scroll %s doc=%s: %s", name, document_id, exc)
    return out[:limit]


async def list_all_indexed_points(*, limit: int = 500) -> list[dict[str, Any]]:
    """Scroll Qdrant — все точки (без фильтра document_id)."""
    return await list_indexed_points(None, limit=limit)


def keyword_search(
    graph: dict[str, Any],
    query: str,
    *,
    limit: int = 10,
    layers: list[str] | None = None,
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Поиск по подстроке в текстовых полях узлов графа."""
    q = query.strip().lower()
    if not q:
        return []
    nodes = (graph or {}).get("nodes") or []
    hits: list[dict[str, Any]] = []
    tokens = [t for t in re.split(r"\s+", q) if t]

    for node in nodes:
        label = str(node.get("label") or "")
        layer = _node_layer(node)
        if layers and layer not in layers:
            continue
        if labels and label not in labels:
            continue
        text = _node_text(node)
        if not text:
            continue
        text_l = text.lower()
        if q in text_l:
            score = 1.0
        elif all(t in text_l for t in tokens):
            score = 0.7
        elif any(t in text_l for t in tokens):
            score = 0.4
        else:
            continue
        hits.append(
            {
                "node_id": str(node.get("id")),
                "neo4j_node_id": str(node.get("id")),
                "label": label,
                "layer": layer,
                "score": score,
                "text": text[:500],
                "props": node.get("props") or {},
                "mode": "keyword",
            }
        )

    hits.sort(key=lambda h: (-h["score"], h["node_id"]))
    return hits[:limit]


def _doc_filter(
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    layer: str | None = None,
) -> Filter | None:
    must: list[FieldCondition] = []
    if document_id:
        must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
    elif document_ids:
        must.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
    if layer:
        must.append(FieldCondition(key="layer", match=MatchValue(value=layer)))
    return Filter(must=must) if must else None


async def _qdrant_semantic(
    query_vector: list[float],
    collection: str,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    layer: str | None = None,
    limit: int = 10,
    retrieval_factor: str = "semantic",
) -> list[dict[str, Any]]:
    qdrant = QdrantClientSingleton.instance().client
    filt = _doc_filter(document_id=document_id, document_ids=document_ids, layer=layer)
    try:
        results = await qdrant.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=filt,
            limit=limit,
            with_payload=True,
        )
    except Exception as exc:
        log.warning("qdrant search %s: %s", collection, exc)
        return []
    hits: list[dict[str, Any]] = []
    for point in results:
        payload = dict(point.payload or {})
        hits.append(
            _search_hit(
                payload,
                score=float(point.score or 0),
                mode="semantic",
                retrieval_factors=[retrieval_factor],
            )
        )
    return hits


async def _scroll_l4_cluster_points(
    document_id: str,
    cluster_id: int,
    *,
    exclude_node_ids: set[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Точки того же L4-кластера из mkg_claims (без векторного поиска)."""
    settings = get_settings()
    qdrant = QdrantClientSingleton.instance().client
    scroll_filter = Filter(
        must=[
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
            FieldCondition(key="layer", match=MatchValue(value="L4")),
            FieldCondition(key="cluster_id", match=MatchValue(value=cluster_id)),
        ]
    )
    exclude = exclude_node_ids or set()
    out: list[dict[str, Any]] = []
    offset = None
    while len(out) < limit:
        try:
            records, offset = await qdrant.scroll(
                collection_name=settings.qdrant_collection_claims,
                scroll_filter=scroll_filter,
                limit=min(32, limit - len(out)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            log.warning("qdrant scroll cluster doc=%s cid=%s: %s", document_id, cluster_id, exc)
            break
        for rec in records:
            payload = dict(rec.payload or {})
            node_id = str(payload.get("neo4j_node_id") or payload.get("node_id") or "")
            if not node_id or node_id in exclude:
                continue
            out.append(payload)
            if len(out) >= limit:
                break
        if offset is None or not records:
            break
    return out


async def combined_semantic_search(
    query: str,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    graph: dict[str, Any] | None = None,
    limit: int = 10,
    layers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Двухфакторный поиск: L3 эмбеддинги + L4 эмбеддинги и контекст кластера HDBSCAN."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return []

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    query_vector = await llm.embed(query, kind="query")

    want_l3 = not layers or "L3" in layers
    want_l4 = not layers or "L4" in layers
    l3_limit = max(4, limit) if want_l3 else 0
    l4_limit = max(3, limit // 2 + 2) if want_l4 else 0

    l3_hits: list[dict[str, Any]] = []
    l4_hits: list[dict[str, Any]] = []
    if want_l3:
        l3_hits = await _qdrant_semantic(
            query_vector,
            settings.qdrant_collection_chunks,
            document_id=document_id,
            document_ids=document_ids,
            layer="L3",
            limit=l3_limit,
            retrieval_factor="l3_embedding",
        )
    if want_l4:
        l4_hits = await _qdrant_semantic(
            query_vector,
            settings.qdrant_collection_claims,
            document_id=document_id,
            document_ids=document_ids,
            layer="L4",
            limit=l4_limit,
            retrieval_factor="l4_embedding",
        )

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for hit in l3_hits + l4_hits:
        merged[_hit_key(hit)] = _merge_hit(merged.get(_hit_key(hit)), hit)

    graphs_by_doc: dict[str, dict[str, Any]] = {}
    if graph and document_id:
        graphs_by_doc[document_id] = graph

    if want_l3 and want_l4:
        l3_by_doc: dict[str, set[str]] = {}
        for hit in l3_hits:
            doc = str(hit.get("document_id") or document_id or "")
            nid = str(hit.get("node_id") or "")
            if doc and nid:
                l3_by_doc.setdefault(doc, set()).add(nid)

        for doc_id, l3_ids in l3_by_doc.items():
            g = graphs_by_doc.get(doc_id)
            if not g:
                g = get_repo().read_graph(doc_id) or {}
                if g.get("nodes"):
                    graphs_by_doc[doc_id] = g
            if not g.get("nodes"):
                continue
            base_score = max((float(h.get("score") or 0) for h in l3_hits if h.get("document_id") == doc_id), default=0.3)
            for bridge in _linked_l4_from_graph(g, l3_ids):
                node = {
                    "id": bridge["node_id"],
                    "label": bridge["label"],
                    "props": {
                        "cluster_id": bridge.get("cluster_id"),
                        "is_anomaly": bridge.get("is_anomaly"),
                        "anomaly_score": bridge.get("anomaly_score"),
                        "text": bridge.get("text"),
                    },
                }
                gh = _graph_hit_from_node(node, document_id=doc_id, score=base_score * 0.75)
                merged[_hit_key(gh)] = _merge_hit(merged.get(_hit_key(gh)), gh)

    if want_l4:
        seen_clusters: set[tuple[str, int]] = set()
        for hit in list(merged.values()):
            if str(hit.get("layer")) != "L4":
                continue
            cid = hit.get("cluster_id")
            if cid is None:
                continue
            try:
                cluster_int = int(cid)
            except (TypeError, ValueError):
                continue
            if cluster_int < 0:
                continue
            doc_id = str(hit.get("document_id") or document_id or "")
            if not doc_id:
                continue
            key = (doc_id, cluster_int)
            if key in seen_clusters:
                continue
            seen_clusters.add(key)
            seed_score = float(hit.get("score") or 0.3)
            exclude = {str(h.get("node_id") or "") for h in merged.values() if h.get("document_id") == doc_id}
            for payload in await _scroll_l4_cluster_points(
                doc_id, cluster_int, exclude_node_ids=exclude, limit=6,
            ):
                ch = _search_hit(
                    payload,
                    score=seed_score * 0.55,
                    mode="semantic",
                    retrieval_factors=["l4_cluster"],
                )
                merged[_hit_key(ch)] = _merge_hit(merged.get(_hit_key(ch)), ch)

    out = sorted(merged.values(), key=lambda h: (-float(h.get("score") or 0), str(h.get("node_id"))))
    return out[:limit]


async def search_chat_retrieval(
    query: str,
    *,
    limit: int = 5,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Чат-поиск: L3 эмбеддинги + L4 эмбеддинги/кластеры, разбивка по факторам."""
    if document_ids:
        indexed_total = 0
        for doc_id in document_ids:
            counts = await count_indexed_points(document_id=doc_id)
            indexed_total += sum(counts.values())
    else:
        counts = await count_indexed_points()
        indexed_total = sum(counts.values())

    all_hits = await combined_semantic_search(
        query,
        document_ids=document_ids,
        limit=max(limit * 2, 10),
    )

    def _has_factor(hit: dict[str, Any], factor: str) -> bool:
        return factor in (hit.get("retrieval_factors") or [])

    l3_hits = [h for h in all_hits if str(h.get("layer")) == "L3" or _has_factor(h, "l3_embedding")]
    l4_hits = [h for h in all_hits if str(h.get("layer")) == "L4" and _has_factor(h, "l4_embedding")]
    cluster_hits = [
        h for h in all_hits
        if _has_factor(h, "l4_cluster") or _has_factor(h, "l4_graph_bridge")
    ]
    cluster_ids: list[int] = []
    for h in all_hits:
        cid = h.get("cluster_id")
        if cid is None:
            continue
        try:
            cluster_int = int(cid)
        except (TypeError, ValueError):
            continue
        if cluster_int >= 0 and cluster_int not in cluster_ids:
            cluster_ids.append(cluster_int)

    return {
        "l3_hits": l3_hits[:limit],
        "l4_hits": l4_hits[:limit],
        "cluster_hits": cluster_hits[:limit],
        "all_hits": all_hits[: max(limit, 8)],
        "indexed_total": indexed_total,
        "cluster_ids": sorted(cluster_ids),
    }


async def semantic_search(
    document_id: str,
    query: str,
    *,
    limit: int = 10,
    layers: list[str] | None = None,
    graph: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Семантический поиск: L3 chunks + L4 claims + контекст кластера."""
    g = graph
    if g is None:
        g = get_repo().read_graph(document_id) or {}
    return await combined_semantic_search(
        query,
        document_id=document_id,
        graph=g if g.get("nodes") else None,
        limit=limit,
        layers=layers,
    )


async def semantic_search_global(
    query: str,
    *,
    limit: int = 10,
    layers: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Глобальный двухфакторный поиск по Qdrant."""
    return await combined_semantic_search(
        query,
        document_ids=document_ids,
        limit=limit,
        layers=layers,
    )


async def search_global(
    query: str,
    *,
    limit: int = 10,
    mode: SearchMode = "auto",
    layers: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Поиск по всей базе Qdrant (semantic). Keyword по всем графам не поддерживается."""
    settings = get_settings()
    can_semantic = bool(settings.yandex_api_key and settings.yandex_folder_id)
    used_mode: SearchMode = mode

    if mode in ("auto", "semantic") and can_semantic:
        semantic_hits = await semantic_search_global(
            query, limit=limit, layers=layers, document_ids=document_ids,
        )
        if semantic_hits or mode == "semantic":
            used_mode = "semantic"
            return {"mode": used_mode, "hits": semantic_hits}

    if mode == "semantic":
        return {"mode": "semantic", "hits": []}

    return {
        "mode": "unavailable",
        "hits": [],
        "note": "Глобальный keyword-поиск недоступен. Настройте Yandex embeddings или выберите документ.",
    }


async def search_document(
    document_id: str,
    graph: dict[str, Any] | None,
    query: str,
    *,
    limit: int = 10,
    mode: SearchMode = "auto",
    layers: list[str] | None = None,
    index_if_missing: bool = True,
) -> dict[str, Any]:
    """Унифицированный поиск: semantic (Qdrant) или keyword fallback."""
    settings = get_settings()
    used_mode: SearchMode = mode
    index_stats: dict[str, Any] | None = None

    if index_if_missing and graph:
        counts = await count_indexed_points(document_id=document_id)
        total_indexed = sum(counts.values())
        if total_indexed == 0:
            index_stats = await index_document_graph(document_id, graph)

    can_semantic = bool(settings.yandex_api_key and settings.yandex_folder_id)
    semantic_hits: list[dict[str, Any]] = []

    if mode in ("auto", "semantic") and can_semantic:
        counts = await count_indexed_points(document_id=document_id)
        if sum(counts.values()) > 0:
            semantic_hits = await semantic_search(
                document_id, query, limit=limit, layers=layers, graph=graph,
            )
            if semantic_hits:
                used_mode = "semantic"

    if semantic_hits:
        return {"mode": used_mode, "hits": semantic_hits, "index": index_stats}

    if mode == "semantic" and not semantic_hits:
        used_mode = "keyword"

    kw_hits = keyword_search(graph or {}, query, limit=limit, layers=layers)
    return {"mode": used_mode if mode != "auto" else "keyword", "hits": kw_hits, "index": index_stats}


async def embedding_status(document_id: str | None = None) -> dict[str, Any]:
    """Где живут эмбеддинги и текущая статистика (опционально по документу)."""
    from mkg_core.runtime_config import get_emb_doc_model, get_emb_query_model, get_llm_model, get_ocr_model

    settings = get_settings()
    counts = await count_indexed_points(document_id=document_id)
    return {
        "provider": "yandex",
        "embed_doc_model": await get_emb_doc_model(),
        "embed_query_model": await get_emb_query_model(),
        "llm_model": await get_llm_model(),
        "ocr_model": await get_ocr_model(),
        "embed_client": "packages/core/src/mkg_core/llm.py::YandexLLMClient.embed",
        "qdrant_url": settings.qdrant_url,
        "document_id": document_id,
        "collections": {
            settings.qdrant_collection_chunks: {
                "purpose": "L3 TextParagraph — только эмбеддинг-поиск (без HDBSCAN)",
                "points": counts.get(settings.qdrant_collection_chunks, 0),
            },
            settings.qdrant_collection_claims: {
                "purpose": "L4 nodes — эмбеддинги + HDBSCAN cluster_id / is_anomaly",
                "points": counts.get(settings.qdrant_collection_claims, 0),
            },
        },
        "vector_size": settings.qdrant_vector_size,
        "yandex_configured": bool(settings.yandex_api_key and settings.yandex_folder_id),
        "auto_index_on_search": True,
        "pipeline_auto_index": True,
        "search_factors": ["l3_embedding", "l4_embedding", "l4_graph_bridge", "l4_cluster"],
        "note": (
            "L3: семантический поиск по mkg_chunks. "
            "L4: HDBSCAN-кластеризация по mkg_claims; поиск объединяет оба фактора."
        ),
    }
