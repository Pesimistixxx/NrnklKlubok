"""Индексация и семантический поиск по TextParagraph / Claim / Entity в Qdrant.

Клиент эмбеддингов: ``YandexLLMClient.embed()`` (text-search-doc / text-search-query).
Коллекции Qdrant: ``mkg_chunks`` (L3 абзацы), ``mkg_claims`` (L4 утверждения),
``mkg_entities`` (Material/Process/Equipment/TechnologySolution/Expert/Measurement).

После extraction worker вызывает ``index_document_graph`` (L3 → mkg_chunks,
L4 → mkg_claims, сущности → mkg_entities). Backfill: ``POST /api/v1/admin/reindex``.
"""
from __future__ import annotations

import asyncio
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
from mkg_core.doc_metadata import qdrant_meta_payload
from mkg_core.store import get_repo

log = logging.getLogger(__name__)

SearchMode = Literal["auto", "semantic", "keyword"]

ENTITY_LABELS = frozenset({
    "Material", "Process", "Equipment", "TechnologySolution", "Expert", "Measurement",
})
_LEXICAL_TOKEN_RE = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)

_TEXT_KEYS = ("raw_text_ru", "quote", "text", "name_ru", "title_ru", "value", "name")

_CLASSIFICATION_LEVELS = frozenset({"открытый", "внутренний", "конфиденциальный", "строго"})


def _normalize_doc_classification(value: str | None) -> str:
    raw = (value or "открытый").strip().lower()
    if raw in _CLASSIFICATION_LEVELS:
        return raw
    aliases = {
        "public": "открытый",
        "internal": "внутренний",
        "confidential": "конфиденциальный",
        "restricted": "строго",
    }
    return aliases.get(raw, "открытый")


def _doc_classification(doc_id: str) -> str:
    rec = get_repo().get(doc_id) or {}
    return _normalize_doc_classification(rec.get("classification"))


def _filter_hits_by_classifications(
    hits: list[dict[str, Any]],
    allowed_classifications: list[str] | None,
) -> list[dict[str, Any]]:
    if not allowed_classifications:
        return hits
    allowed = set(allowed_classifications)
    out: list[dict[str, Any]] = []
    for hit in hits:
        doc_id = str(hit.get("document_id") or "")
        if not doc_id or _doc_classification(doc_id) in allowed:
            out.append(hit)
    return out


def _filter_document_ids(
    doc_ids: list[str],
    allowed_classifications: list[str] | None,
) -> list[str]:
    if not allowed_classifications:
        return doc_ids
    allowed = set(allowed_classifications)
    return [doc_id for doc_id in doc_ids if _doc_classification(doc_id) in allowed]


def _base_qdrant_payload(document_id: str, **extra: Any) -> dict[str, Any]:
    rec = get_repo().get(document_id) or {}
    payload = qdrant_meta_payload(rec)
    payload["document_id"] = document_id
    payload.update(extra)
    return payload


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


def _entity_index_text(node: dict[str, Any]) -> str:
    """Текст для эмбеддинга сущности: имя + описание + синонимы (+ quote для Measurement)."""
    label = str(node.get("label") or "")
    props = node.get("props") or {}
    parts: list[str] = []

    if label == "Expert":
        for key in ("full_name", "name_ru", "name", "affiliation", "organization", "role"):
            val = props.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
    elif label == "Measurement":
        for key in ("description", "quote", "text", "parameter_name"):
            val = props.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        num = props.get("numeric_value")
        unit = props.get("unit")
        if num is not None:
            parts.append(f"{num} {unit or ''}".strip())
    else:
        for key in ("name_ru", "name_en", "name", "chemical_formula", "title_ru", "title"):
            val = props.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        desc = props.get("description")
        if isinstance(desc, str) and desc.strip():
            parts.append(desc.strip())
        quote = props.get("quote")
        if isinstance(quote, str) and quote.strip():
            parts.append(quote.strip())

    aliases = props.get("aliases")
    if isinstance(aliases, list):
        for item in aliases:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
    elif isinstance(aliases, str) and aliases.strip():
        parts.append(aliases.strip())

    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        key = part.lower()
        if key not in seen:
            seen.add(key)
            out.append(part)
    return " · ".join(out)


def _lexical_tokens(text: str) -> list[str]:
    """Токены для keyword/hybrid-поиска в payload (без BM25, MatchAny по токенам)."""
    tokens = _LEXICAL_TOKEN_RE.findall((text or "").lower())
    return sorted(set(t for t in tokens if len(t) >= 2))


def _short_query_score_threshold(query: str) -> float | None:
    """Порог релевантности для коротких запросов; бытовые реплики не ослабляем."""
    try:
        from mkg_core.query_classify import is_conversational_query

        if is_conversational_query(query):
            return 0.99
    except Exception:
        pass
    tokens = _lexical_tokens(query)
    if len(tokens) <= 2:
        try:
            from mkg_core.alias_expansion import get_alias_lookup

            lookup = get_alias_lookup()
            if any(t in lookup for t in tokens):
                return 0.35
        except Exception:
            pass
        return 0.45
    return None


def _collection_for_layer(layer: str, label: str = "") -> str:
    settings = get_settings()
    if layer == "L4" and label not in ENTITY_LABELS:
        return settings.qdrant_collection_claims
    if label in ENTITY_LABELS or layer in ("L1", "L2"):
        return settings.qdrant_collection_entities
    return settings.qdrant_collection_chunks


def _entity_search_hit(
    payload: dict[str, Any],
    *,
    score: float,
    mode: str = "semantic",
    retrieval_factors: list[str] | None = None,
    collection: str | None = None,
) -> dict[str, Any]:
    node_id = str(payload.get("neo4j_node_id") or payload.get("node_id") or "")
    entity_type = str(payload.get("entity_type") or payload.get("label") or "")
    layer = str(payload.get("layer") or ("L2" if entity_type == "Expert" else "L1"))
    hit: dict[str, Any] = {
        "node_id": node_id,
        "neo4j_node_id": node_id,
        "entity_type": entity_type,
        "label": entity_type,
        "layer": layer,
        "score": score,
        "text": str(payload.get("text") or "")[:500],
        "document_id": str(payload.get("document_id") or ""),
        "geography": payload.get("geography"),
        "tags": payload.get("tags") or [],
        "props": {},
        "mode": mode,
        "collection": collection or get_settings().qdrant_collection_entities,
    }
    if retrieval_factors:
        hit["retrieval_factors"] = list(retrieval_factors)
    return hit


def _search_hit(
    payload: dict[str, Any],
    *,
    score: float,
    mode: str,
    retrieval_factors: list[str] | None = None,
    collection: str | None = None,
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
        "collection": collection or _collection_for_layer(
            str(payload.get("layer") or "L?"),
            str(payload.get("label") or ""),
        ),
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
    for name in (
        settings.qdrant_collection_chunks,
        settings.qdrant_collection_claims,
        settings.qdrant_collection_entities,
    ):
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
                payload=_base_qdrant_payload(
                    document_id,
                    node_id=node_id,
                    neo4j_node_id=node_id,
                    label="TextParagraph",
                    layer="L3",
                    text=text[:2000],
                    lexical_tokens=_lexical_tokens(text),
                    md_file=repo.markdown_relative_path(document_id),
                    source="markdown",
                ),
            )
        )
        indexed += 1

    batch_size = 32
    for i in range(0, len(points), batch_size):
        await qdrant.upsert(collection_name=collection, points=points[i : i + batch_size])

    return {"indexed": indexed, "skipped": skipped}


async def index_document_graph(document_id: str, graph: dict[str, Any] | None) -> dict[str, int]:
    """Эмбеддит TextParagraph (L3) и все L4-узлы графа в Qdrant."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return {"indexed": 0, "indexed_l3": 0, "indexed_l4": 0, "skipped": 0, "error": "YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы"}

    nodes = (graph or {}).get("nodes") or []
    indexable = [n for n in nodes if str(n.get("label")) in _indexable_labels() and _node_text(n)]

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    qdrant = QdrantClientSingleton.instance().client

    if not indexable:
        entity_stats = await index_document_entities(document_id, graph)
        return {
            "indexed": entity_stats.get("indexed", 0),
            "indexed_l3": 0,
            "indexed_l4": 0,
            "indexed_entities": entity_stats.get("indexed", 0),
            "skipped": entity_stats.get("skipped", 0),
            "collections": {
                settings.qdrant_collection_chunks: 0,
                settings.qdrant_collection_claims: 0,
                settings.qdrant_collection_entities: entity_stats.get("indexed", 0),
            },
        }

    by_collection: dict[str, list[PointStruct]] = {}
    indexed = 0
    indexed_l3 = 0
    indexed_l4 = 0
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
        layer = _node_layer(node)
        repo = get_repo()
        point = PointStruct(
            id=_point_id(node_id),
            vector=vector,
            payload=_base_qdrant_payload(
                document_id,
                node_id=node_id,
                neo4j_node_id=node_id,
                label=label,
                layer=layer,
                text=text[:2000],
                lexical_tokens=_lexical_tokens(text),
                md_file=repo.markdown_relative_path(document_id),
            ),
        )
        by_collection.setdefault(collection, []).append(point)
        indexed += 1
        if label in L4_LABELS:
            indexed_l4 += 1
        else:
            indexed_l3 += 1

    for collection, points in by_collection.items():
        batch_size = 32
        for i in range(0, len(points), batch_size):
            await qdrant.upsert(collection_name=collection, points=points[i : i + batch_size])

    entity_stats = await index_document_entities(document_id, graph)

    return {
        "indexed": indexed + entity_stats.get("indexed", 0),
        "indexed_l3": indexed_l3,
        "indexed_l4": indexed_l4,
        "indexed_entities": entity_stats.get("indexed", 0),
        "skipped": skipped + entity_stats.get("skipped", 0),
        "collections": {
            settings.qdrant_collection_chunks: indexed_l3,
            settings.qdrant_collection_claims: indexed_l4,
            settings.qdrant_collection_entities: entity_stats.get("indexed", 0),
        },
    }


async def index_document_entities(document_id: str, graph: dict[str, Any] | None) -> dict[str, int]:
    """Эмбеддит L1/L2 Expert и L4 Measurement + L1 сущности в mkg_entities — без cluster_id."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return {"indexed": 0, "skipped": 0, "error": "YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы"}

    nodes = (graph or {}).get("nodes") or []
    indexable = [
        n for n in nodes
        if str(n.get("label")) in ENTITY_LABELS and _entity_index_text(n)
    ]
    if not indexable:
        return {"indexed": 0, "skipped": 0}

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    qdrant = QdrantClientSingleton.instance().client
    collection = settings.qdrant_collection_entities
    repo = get_repo()
    points: list[PointStruct] = []
    indexed = 0
    skipped = 0

    for node in indexable:
        label = str(node.get("label"))
        node_id = str(node.get("id") or "")
        text = _entity_index_text(node)
        if not node_id or not text:
            skipped += 1
            continue
        try:
            vector = await llm.embed(text[:8000], kind="doc")
        except Exception as exc:
            log.warning("entity embed failed node=%s: %s", node_id, exc)
            skipped += 1
            continue
        layer = "L2" if label == "Expert" else ("L4" if label == "Measurement" else "L1")
        points.append(
            PointStruct(
                id=_point_id(node_id),
                vector=vector,
                payload=_base_qdrant_payload(
                    document_id,
                    node_id=node_id,
                    neo4j_node_id=node_id,
                    entity_type=label,
                    label=label,
                    layer=layer,
                    text=text[:2000],
                    lexical_tokens=_lexical_tokens(text),
                    md_file=repo.markdown_relative_path(document_id),
                    source="graph_entity",
                ),
            )
        )
        indexed += 1

    batch_size = 32
    for i in range(0, len(points), batch_size):
        await qdrant.upsert(collection_name=collection, points=points[i : i + batch_size])

    return {"indexed": indexed, "skipped": skipped, "collection": collection}


async def reindex_document_entities(document_id: str, graph: dict[str, Any] | None = None) -> dict[str, int]:
    """Переиндексация mkg_entities для одного документа."""
    g = graph if graph is not None else (get_repo().read_graph(document_id) or {})
    return await index_document_entities(document_id, g if g.get("nodes") else None)


async def reindex_corpus_entities(document_ids: list[str] | None = None) -> dict[str, Any]:
    """Backfill mkg_entities для корпуса (все документы или указанный список)."""
    repo = get_repo()
    if document_ids:
        ids = [d for d in document_ids if d]
    else:
        ids = [
            item["id"]
            for item in (repo.list(page=1, page_size=500)[0] or [])
            if item.get("id")
        ]
    out: dict[str, Any] = {
        "documents": 0,
        "indexed": 0,
        "skipped": 0,
        "collection": get_settings().qdrant_collection_entities,
        "per_document": [],
        "errors": [],
    }
    for doc_id in ids:
        graph = repo.read_graph(doc_id)
        if not graph or not graph.get("nodes"):
            continue
        try:
            stats = await index_document_entities(doc_id, graph)
            out["documents"] += 1
            out["indexed"] += int(stats.get("indexed") or 0)
            out["skipped"] += int(stats.get("skipped") or 0)
            out["per_document"].append({"document_id": doc_id, **stats})
        except Exception as exc:
            log.warning("reindex entities doc=%s: %s", doc_id, exc)
            out["errors"].append({"document_id": doc_id, "error": str(exc)})
    return out


async def reindex_corpus(document_ids: list[str] | None = None) -> dict[str, Any]:
    """Полная переиндексация L3+L4+entities для корпуса."""
    repo = get_repo()
    if document_ids:
        ids = [d for d in document_ids if d]
    else:
        ids = [
            item["id"]
            for item in (repo.list(page=1, page_size=500)[0] or [])
            if item.get("id")
        ]
    out: dict[str, Any] = {
        "documents": 0,
        "indexed_l3": 0,
        "indexed_l4": 0,
        "indexed_entities": 0,
        "skipped": 0,
        "per_document": [],
        "errors": [],
    }
    for doc_id in ids:
        graph = repo.read_graph(doc_id)
        if not graph or not graph.get("nodes"):
            md = repo.read_markdown(doc_id)
            if md:
                try:
                    stats = await index_document_markdown(doc_id, md)
                    out["documents"] += 1
                    out["indexed_l3"] += int(stats.get("indexed") or 0)
                    out["skipped"] += int(stats.get("skipped") or 0)
                    out["per_document"].append({"document_id": doc_id, **stats})
                except Exception as exc:
                    out["errors"].append({"document_id": doc_id, "error": str(exc)})
            continue
        try:
            stats = await index_document_graph(doc_id, graph)
            out["documents"] += 1
            out["indexed_l3"] += int(stats.get("indexed_l3") or 0)
            out["indexed_l4"] += int(stats.get("indexed_l4") or 0)
            out["indexed_entities"] += int(stats.get("indexed_entities") or 0)
            out["skipped"] += int(stats.get("skipped") or 0)
            out["per_document"].append({"document_id": doc_id, **stats})
        except Exception as exc:
            log.warning("reindex corpus doc=%s: %s", doc_id, exc)
            out["errors"].append({"document_id": doc_id, "error": str(exc)})
    return out


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
        settings.qdrant_collection_entities,
    ]
    filt: Filter | None = None
    if document_id is not None:
        filt = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    out: list[dict[str, Any]] = []
    allowed = {
        settings.qdrant_collection_chunks,
        settings.qdrant_collection_claims,
        settings.qdrant_collection_entities,
    }
    for name in names:
        if name not in allowed:
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
                        "label": payload.get("label") or payload.get("entity_type"),
                        "entity_type": payload.get("entity_type"),
                        "layer": payload.get("layer"),
                        "text": (payload.get("text") or "")[:300],
                        "cluster_id": payload.get("cluster_id"),
                        "cluster_name": payload.get("cluster_name"),
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
    # Для коротких запросов — полное совпадение; для расширенных alias — достаточно ключевого токена.
    primary_tokens = tokens[:3] if len(tokens) > 4 else tokens

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
        elif primary_tokens and all(t in text_l for t in primary_tokens):
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


async def _qdrant_vector_search(
    qdrant: Any,
    *,
    collection_name: str,
    query: list[float],
    query_filter: Filter | None = None,
    limit: int = 10,
    score_threshold: float | None = None,
) -> list[Any]:
    """Vector similarity search via query_points (qdrant-client 1.7+)."""
    kwargs: dict[str, Any] = {
        "collection_name": collection_name,
        "query": query,
        "limit": limit,
        "with_payload": True,
    }
    if query_filter is not None:
        kwargs["query_filter"] = query_filter
    if score_threshold is not None:
        kwargs["score_threshold"] = score_threshold
    response = await qdrant.query_points(**kwargs)
    return list(response.points or [])


async def _qdrant_semantic(
    query_vector: list[float],
    collection: str,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    layer: str | None = None,
    limit: int = 10,
    retrieval_factor: str = "semantic",
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    qdrant = QdrantClientSingleton.instance().client
    filt = _doc_filter(document_id=document_id, document_ids=document_ids, layer=layer)
    try:
        results = await _qdrant_vector_search(
            qdrant,
            collection_name=collection,
            query=query_vector,
            query_filter=filt,
            limit=limit,
            score_threshold=score_threshold,
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
                collection=collection,
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


async def _chunk_keyword_hits(
    query: str,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    layer: str | None = "L3",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Keyword-поиск по lexical_tokens в mkg_chunks (fallback для коротких запросов)."""
    settings = get_settings()
    q_tokens = _lexical_tokens(query)
    if not q_tokens:
        return []
    qdrant = QdrantClientSingleton.instance().client
    filt = _doc_filter(document_id=document_id, document_ids=document_ids, layer=layer)
    must = list(filt.must) if filt else []
    must.append(FieldCondition(key="lexical_tokens", match=MatchAny(any=q_tokens[:16])))
    scroll_filter = Filter(must=must)
    out: list[dict[str, Any]] = []
    offset = None
    while len(out) < limit:
        try:
            records, offset = await qdrant.scroll(
                collection_name=settings.qdrant_collection_chunks,
                scroll_filter=scroll_filter,
                limit=min(32, limit - len(out)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            log.warning("chunk keyword scroll: %s", exc)
            break
        for rec in records:
            payload = dict(rec.payload or {})
            text_l = str(payload.get("text") or "").lower()
            overlap = sum(1 for t in q_tokens if t in text_l or t in (payload.get("lexical_tokens") or []))
            score = min(1.0, 0.35 + 0.15 * overlap)
            out.append(
                _search_hit(
                    payload,
                    score=score,
                    mode="keyword",
                    retrieval_factors=["l3_keyword"],
                )
            )
            if len(out) >= limit:
                break
        if offset is None or not records:
            break
    out.sort(key=lambda h: (-float(h.get("score") or 0), str(h.get("node_id"))))
    return out[:limit]


async def combined_semantic_search(
    query: str,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    graph: dict[str, Any] | None = None,
    limit: int = 10,
    layers: list[str] | None = None,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    """Двухфакторный поиск: L3 эмбеддинги + L4 эмбеддинги и контекст кластера HDBSCAN."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return []

    q = (query or "").strip()
    if not q:
        return []

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    query_vector = await llm.embed(q, kind="query")

    effective_threshold = score_threshold
    if effective_threshold is None:
        effective_threshold = _short_query_score_threshold(q)

    want_l3 = not layers or "L3" in layers
    want_l4 = not layers or "L4" in layers
    l3_limit = max(6, limit) if want_l3 else 0
    l4_limit = max(4, limit // 2 + 3) if want_l4 else 0

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
            score_threshold=effective_threshold,
        )
        if len(l3_hits) < l3_limit:
            kw_merged: dict[tuple[str, str], dict[str, Any]] = {_hit_key(h): h for h in l3_hits}
            for hit in await _chunk_keyword_hits(
                q,
                document_id=document_id,
                document_ids=document_ids,
                layer="L3",
                limit=l3_limit,
            ):
                kw_merged[_hit_key(hit)] = _merge_hit(kw_merged.get(_hit_key(hit)), hit)
            l3_hits = sorted(kw_merged.values(), key=lambda h: (-float(h.get("score") or 0), str(h.get("node_id"))))[:l3_limit]
    if want_l4:
        l4_hits = await _qdrant_semantic(
            query_vector,
            settings.qdrant_collection_claims,
            document_id=document_id,
            document_ids=document_ids,
            layer="L4",
            limit=l4_limit,
            retrieval_factor="l4_embedding",
            score_threshold=effective_threshold,
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


def _entity_filter(
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    types: list[str] | None = None,
) -> Filter | None:
    must: list[FieldCondition] = []
    if document_id:
        must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
    elif document_ids:
        must.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
    if types:
        allowed = [t for t in types if t in ENTITY_LABELS]
        if allowed:
            must.append(FieldCondition(key="entity_type", match=MatchAny(any=allowed)))
    return Filter(must=must) if must else None


async def _entity_keyword_hits(
    query: str,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    types: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Keyword-поиск по lexical_tokens в mkg_entities (fallback / hybrid)."""
    settings = get_settings()
    q_tokens = _lexical_tokens(query)
    if not q_tokens:
        return []
    qdrant = QdrantClientSingleton.instance().client
    filt = _entity_filter(document_id=document_id, document_ids=document_ids, types=types)
    must = list(filt.must) if filt else []
    must.append(FieldCondition(key="lexical_tokens", match=MatchAny(any=q_tokens[:16])))
    scroll_filter = Filter(must=must)
    out: list[dict[str, Any]] = []
    offset = None
    while len(out) < limit:
        try:
            records, offset = await qdrant.scroll(
                collection_name=settings.qdrant_collection_entities,
                scroll_filter=scroll_filter,
                limit=min(32, limit - len(out)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            log.warning("entity keyword scroll: %s", exc)
            break
        for rec in records:
            payload = dict(rec.payload or {})
            text_l = str(payload.get("text") or "").lower()
            overlap = sum(1 for t in q_tokens if t in text_l or t in (payload.get("lexical_tokens") or []))
            score = min(1.0, 0.35 + 0.15 * overlap)
            out.append(
                _entity_search_hit(
                    payload,
                    score=score,
                    mode="keyword",
                    retrieval_factors=["entity_keyword"],
                )
            )
            if len(out) >= limit:
                break
        if offset is None or not records:
            break
    out.sort(key=lambda h: (-float(h.get("score") or 0), str(h.get("node_id"))))
    return out[:limit]


async def search_entities(
    query: str,
    *,
    types: list[str] | None = None,
    limit: int = 20,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    """Семантический (+ keyword hybrid) поиск Material/Process в mkg_entities. Без L4-кластеров."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return await _entity_keyword_hits(
            query,
            document_id=document_id,
            document_ids=document_ids,
            types=types,
            limit=limit,
        )

    q = (query or "").strip()
    if not q:
        return []

    entity_types = [t for t in (types or list(ENTITY_LABELS)) if t in ENTITY_LABELS]
    if not entity_types:
        entity_types = list(ENTITY_LABELS)

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    query_vector = await llm.embed(q, kind="query")
    qdrant = QdrantClientSingleton.instance().client
    filt = _entity_filter(
        document_id=document_id,
        document_ids=document_ids,
        types=entity_types,
    )
    semantic_hits: list[dict[str, Any]] = []
    try:
        results = await _qdrant_vector_search(
            qdrant,
            collection_name=settings.qdrant_collection_entities,
            query=query_vector,
            query_filter=filt,
            limit=limit,
            score_threshold=score_threshold,
        )
        for point in results:
            payload = dict(point.payload or {})
            semantic_hits.append(
                _entity_search_hit(
                    payload,
                    score=float(point.score or 0),
                    mode="semantic",
                    retrieval_factors=["entity_embedding"],
                )
            )
    except Exception as exc:
        log.warning("entity semantic search: %s", exc)

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for hit in semantic_hits:
        merged[_hit_key(hit)] = _merge_hit(merged.get(_hit_key(hit)), hit)

    if len(merged) < limit:
        for hit in await _entity_keyword_hits(
            q,
            document_id=document_id,
            document_ids=document_ids,
            types=entity_types,
            limit=limit,
        ):
            merged[_hit_key(hit)] = _merge_hit(merged.get(_hit_key(hit)), hit)

    out = sorted(merged.values(), key=lambda h: (-float(h.get("score") or 0), str(h.get("node_id"))))
    return out[:limit]


async def search_chat_retrieval(
    query: str,
    *,
    limit: int = 9,
    document_ids: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
    fast: bool = False,
    allowed_classifications: list[str] | None = None,
) -> dict[str, Any]:
    """Чат-поиск: L3 эмбеддинги + L4 эмбеддинги/кластеры, разбивка по факторам."""
    from mkg_core.graph_traversal import keyword_seeds_from_docs, neo4j_keyword_seeds
    from mkg_core.search_query import effective_search_query, search_query_variants

    raw_q = query.strip()
    search_q = effective_search_query(query, history)
    query_variants = search_query_variants(query, history)
    scoped = _filter_document_ids([d for d in (document_ids or []) if d], allowed_classifications)

    try:
        from mkg_core.query_classify import is_conversational_query

        if is_conversational_query(raw_q):
            if scoped:
                indexed_total = 0
                for doc_id in scoped:
                    counts = await count_indexed_points(document_id=doc_id)
                    indexed_total += sum(counts.values())
            else:
                counts = await count_indexed_points()
                indexed_total = sum(counts.values())
            return {
                "l3_hits": [],
                "l4_hits": [],
                "entity_hits": [],
                "cluster_hits": [],
                "all_hits": [],
                "indexed_total": indexed_total,
                "cluster_ids": [],
                "search_query": raw_q,
                "fallback": "conversational_skip",
            }
    except Exception:
        pass

    if scoped:
        indexed_total = 0
        for doc_id in scoped:
            counts = await count_indexed_points(document_id=doc_id)
            indexed_total += sum(counts.values())
    else:
        counts = await count_indexed_points()
        indexed_total = sum(counts.values())

    fetch_limit = max(limit + 2, 8) if fast else max(limit * 2, 12)
    all_hits: list[dict[str, Any]] = []
    fallback: str | None = None
    repo = get_repo()
    all_doc_ids = _filter_document_ids(
        [
            item["id"]
            for item in (repo.list(page=1, page_size=200)[0] or [])
            if item.get("id")
        ],
        allowed_classifications,
    )

    async def _unified_hits(
        q: str,
        *,
        doc_scope: list[str] | None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        if not q.strip():
            return []
        result = await search_global(
            q,
            limit=fetch_limit,
            document_ids=doc_scope or None,
            score_threshold=score_threshold,
            allowed_classifications=allowed_classifications,
        )
        return list(result.get("hits") or [])

    variants = query_variants[:1] if fast else query_variants

    if fast and variants:
        variant = variants[0]
        all_hits = await _unified_hits(variant, doc_scope=scoped)
        if not all_hits and scoped and indexed_total == 0:
            global_counts = await count_indexed_points()
            if sum(global_counts.values()) > 0:
                all_hits = await _unified_hits(variant, doc_scope=None)
                if all_hits:
                    fallback = "qdrant_global_retry"
        if not all_hits and scoped:
            fb_hits = keyword_seeds_from_docs(variant, scoped, limit=fetch_limit)
            if not fb_hits and all_doc_ids:
                fb_hits = keyword_seeds_from_docs(variant, all_doc_ids, limit=fetch_limit)
            if not fb_hits:
                fb_hits = await neo4j_keyword_seeds(raw_q or search_q, limit=fetch_limit)
            if fb_hits:
                all_hits = fb_hits
                fallback = "graph_keyword"
    elif variants:
        for variant in variants:
            all_hits = await _unified_hits(variant, doc_scope=scoped)
            if all_hits:
                break

        if not all_hits and scoped and indexed_total == 0:
            global_counts = await count_indexed_points()
            if sum(global_counts.values()) > 0:
                for variant in variants:
                    all_hits = await _unified_hits(variant, doc_scope=None)
                    if all_hits:
                        fallback = "qdrant_global_retry"
                        break

        if not all_hits and scoped:
            for variant in variants:
                all_hits = await _unified_hits(variant, doc_scope=None, score_threshold=0.05)
                if all_hits:
                    fallback = "qdrant_global_retry"
                    break

        if not all_hits:
            fb_hits: list[dict[str, Any]] = []
            fb_global = False
            for variant in variants:
                if scoped:
                    fb_hits = keyword_seeds_from_docs(variant, scoped, limit=fetch_limit)
                if not fb_hits and all_doc_ids:
                    fb_hits = keyword_seeds_from_docs(variant, all_doc_ids, limit=fetch_limit)
                    fb_global = bool(fb_hits and scoped)
                if fb_hits:
                    break
            if not fb_hits:
                fb_hits = await neo4j_keyword_seeds(raw_q or search_q, limit=fetch_limit)
            if fb_hits:
                all_hits = fb_hits
                if fb_global:
                    fallback = "graph_keyword_global"
                elif scoped:
                    fallback = "graph_keyword"
                else:
                    fallback = "graph_keyword" if any(
                        h.get("retrieval_source") == "graph_keyword" for h in fb_hits
                    ) else "neo4j_keyword"
            elif scoped and indexed_total > 0:
                for variant in variants:
                    all_hits = await _unified_hits(
                        variant,
                        doc_scope=None,
                        score_threshold=0.05,
                    )
                    if all_hits:
                        fallback = "qdrant_global_retry"
                        break

    entity_hits: list[dict[str, Any]] = [
        h for h in all_hits
        if str(h.get("layer")) in ("L1", "L2")
        or h.get("collection") == get_settings().qdrant_collection_entities
    ]

    def _has_factor(hit: dict[str, Any], factor: str) -> bool:
        return factor in (hit.get("retrieval_factors") or [])

    l3_hits = [h for h in all_hits if str(h.get("layer")) == "L3" or _has_factor(h, "l3_embedding")]
    l4_hits = [h for h in all_hits if str(h.get("layer")) == "L4" and _has_factor(h, "l4_embedding")]
    entity_only_hits = [
        h for h in all_hits
        if str(h.get("layer")) == "L1"
        and (
            _has_factor(h, "entity_embedding")
            or _has_factor(h, "entity_keyword")
        )
    ]
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

    l3_hits = _filter_hits_by_classifications(l3_hits, allowed_classifications)
    l4_hits = _filter_hits_by_classifications(l4_hits, allowed_classifications)
    entity_hits = _filter_hits_by_classifications(entity_hits, allowed_classifications)
    entity_only_hits = _filter_hits_by_classifications(entity_only_hits, allowed_classifications)
    cluster_hits = _filter_hits_by_classifications(cluster_hits, allowed_classifications)
    all_hits = _filter_hits_by_classifications(all_hits, allowed_classifications)

    return {
        "l3_hits": l3_hits[:limit],
        "l4_hits": l4_hits[:limit],
        "entity_hits": (entity_hits or entity_only_hits)[:limit],
        "cluster_hits": cluster_hits[:limit],
        "all_hits": all_hits[: max(limit, 10)],
        "indexed_total": indexed_total,
        "cluster_ids": sorted(cluster_ids),
        "search_query": search_q,
        "fallback": fallback,
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
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    """Глобальный двухфакторный поиск по Qdrant."""
    threshold = score_threshold
    if threshold is None:
        threshold = _short_query_score_threshold(query)
    return await combined_semantic_search(
        query,
        document_ids=document_ids,
        limit=limit,
        layers=layers,
        score_threshold=threshold,
    )


async def search_global(
    query: str,
    *,
    limit: int = 10,
    mode: SearchMode = "auto",
    layers: list[str] | None = None,
    document_ids: list[str] | None = None,
    include_entities: bool = True,
    score_threshold: float | None = None,
    allowed_classifications: list[str] | None = None,
) -> dict[str, Any]:
    """Поиск по всей базе Qdrant: mkg_chunks + mkg_claims + mkg_entities."""
    settings = get_settings()
    scoped_doc_ids = _filter_document_ids(list(document_ids or []), allowed_classifications)
    can_semantic = bool(settings.yandex_api_key and settings.yandex_folder_id)
    threshold = score_threshold
    if threshold is None:
        threshold = _short_query_score_threshold(query)

    if mode in ("auto", "semantic") and can_semantic:
        semantic_hits = await semantic_search_global(
            query,
            limit=limit,
            layers=layers,
            document_ids=scoped_doc_ids or None,
            score_threshold=threshold,
        )
        entity_hits: list[dict[str, Any]] = []
        want_entities = include_entities and (
            not layers or any(l in layers for l in ("L1", "L2", "L4"))
        )
        if want_entities:
            entity_hits = await search_entities(
                query,
                types=list(ENTITY_LABELS),
                limit=limit,
                document_ids=scoped_doc_ids or None,
                score_threshold=threshold,
            )
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for hit in semantic_hits + entity_hits:
            merged[_hit_key(hit)] = _merge_hit(merged.get(_hit_key(hit)), hit)
        out_hits = sorted(
            merged.values(),
            key=lambda h: (-float(h.get("score") or 0), str(h.get("node_id"))),
        )[:limit]
        out_hits = _filter_hits_by_classifications(out_hits, allowed_classifications)
        counts = await count_indexed_points()
        return {
            "mode": "semantic",
            "hits": out_hits,
            "total": len(out_hits),
            "entity_hits": entity_hits,
            "chunk_hits": [h for h in semantic_hits if str(h.get("layer")) == "L3"],
            "collections": {
                settings.qdrant_collection_chunks: counts.get(settings.qdrant_collection_chunks, 0),
                settings.qdrant_collection_claims: counts.get(settings.qdrant_collection_claims, 0),
                settings.qdrant_collection_entities: counts.get(settings.qdrant_collection_entities, 0),
            },
        }

    if mode == "semantic":
        return {
            "mode": "semantic",
            "hits": [],
            "note": "Yandex embeddings не настроены (YANDEX_API_KEY / YANDEX_FOLDER_ID).",
        }

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
    total_points = sum(counts.values())
    qdrant_ok = False
    try:
        qdrant = QdrantClientSingleton.instance().client
        await qdrant.get_collections()
        qdrant_ok = True
    except Exception as exc:
        log.warning("qdrant health check: %s", exc)

    async def _model(getter) -> str:
        try:
            return await getter()
        except Exception as exc:
            log.warning("runtime config %s: %s", getter.__name__, exc)
            return ""

    return {
        "provider": "yandex",
        "embed_doc_model": await _model(get_emb_doc_model) or settings.yandex_emb_doc or "text-search-doc/latest",
        "embed_query_model": await _model(get_emb_query_model) or settings.yandex_emb_query or "text-search-query/latest",
        "llm_model": await _model(get_llm_model),
        "ocr_model": await _model(get_ocr_model),
        "embed_client": "packages/core/src/mkg_core/llm.py::YandexLLMClient.embed",
        "qdrant_url": settings.qdrant_url,
        "qdrant_ok": qdrant_ok,
        "total_points": total_points,
        "l3_points": counts.get(settings.qdrant_collection_chunks, 0),
        "l4_points": counts.get(settings.qdrant_collection_claims, 0),
        "entity_points": counts.get(settings.qdrant_collection_entities, 0),
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
            settings.qdrant_collection_entities: {
                "purpose": "L1 Material/Process — отдельный индекс, без кластеров",
                "points": counts.get(settings.qdrant_collection_entities, 0),
            },
        },
        "vector_size": settings.qdrant_vector_size,
        "yandex_configured": bool(settings.yandex_api_key and settings.yandex_folder_id),
        "auto_index_on_search": True,
        "pipeline_auto_index": True,
        "search_factors": [
            "l3_embedding", "l3_keyword", "l4_embedding", "l4_graph_bridge", "l4_cluster",
            "entity_embedding", "entity_keyword",
        ],
        "entity_labels": sorted(ENTITY_LABELS),
        "note": (
            "L3: семантический + keyword по mkg_chunks. "
            "L4: HDBSCAN-кластеризация по mkg_claims; поиск объединяет оба фактора. "
            "L1/L2/L4 Measurement: коллекция mkg_entities (Material, Process, Equipment, "
            "TechnologySolution, Expert, Measurement) — без cluster_id."
        ),
    }


def _pca_to_2d(vectors: list[list[float]]) -> list[tuple[float, float]]:
    """Проекция N×D векторов в 2D (PCA через SVD, без sklearn)."""
    import numpy as np

    n = len(vectors)
    if n == 0:
        return []
    if n == 1:
        return [(0.0, 0.0)]
    x = np.asarray(vectors, dtype=np.float64)
    x = x - x.mean(axis=0)
    if np.allclose(x, 0):
        return [(0.0, 0.0)] * n
    try:
        _, _, vt = np.linalg.svd(x, full_matrices=False)
        components = vt[: min(2, vt.shape[0])].T
        if components.shape[1] == 1:
            components = np.hstack([components, np.zeros((components.shape[0], 1))])
        coords = x @ components
    except np.linalg.LinAlgError:
        coords = np.zeros((n, 2))
    return [(float(coords[i, 0]), float(coords[i, 1])) for i in range(n)]


async def fetch_points_with_vectors(
    document_id: str | None = None,
    *,
    limit: int = 500,
    layer: str | None = None,
) -> list[dict[str, Any]]:
    """Scroll Qdrant — точки с векторами для 2D-визуализации."""
    settings = get_settings()
    qdrant = QdrantClientSingleton.instance().client
    if layer == "L4":
        names = [settings.qdrant_collection_claims]
    elif layer == "L3":
        names = [settings.qdrant_collection_chunks]
    else:
        names = [settings.qdrant_collection_chunks, settings.qdrant_collection_claims]
    filt: Filter | None = None
    if document_id is not None:
        filt = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    out: list[dict[str, Any]] = []
    for name in names:
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
                    with_vectors=True,
                )
                for rec in records:
                    payload = dict(rec.payload or {})
                    vector = rec.vector
                    if vector is None:
                        continue
                    if isinstance(vector, dict):
                        vector = next(iter(vector.values()), None)
                    if not vector:
                        continue
                    out.append(
                        {
                            "id": str(rec.id),
                            "collection": name,
                            "point_id": str(rec.id),
                            "node_id": payload.get("node_id"),
                            "neo4j_node_id": payload.get("neo4j_node_id") or payload.get("node_id"),
                            "document_id": payload.get("document_id"),
                            "label": payload.get("label"),
                            "layer": payload.get("layer"),
                            "text": (payload.get("text") or "")[:300],
                            "cluster_id": payload.get("cluster_id"),
                            "cluster_name": payload.get("cluster_name"),
                            "cluster_description": payload.get("cluster_description"),
                            "is_anomaly": payload.get("is_anomaly"),
                            "anomaly_reason": payload.get("anomaly_reason"),
                            "anomaly_score": payload.get("anomaly_score"),
                            "vector": list(vector),
                        }
                    )
                if offset is None or not records:
                    break
        except Exception as exc:
            log.warning("qdrant scroll vectors %s doc=%s: %s", name, document_id, exc)
    return out[:limit]


async def compute_embedding_viz(
    document_id: str | None = None,
    *,
    limit: int = 500,
    layer: str | None = "L4",
) -> dict[str, Any]:
    """PCA-проекция эмбеддингов Qdrant в 2D для UI scatter plot (по умолчанию только L4)."""
    from mkg_core.l4_clustering import get_l4_clustering_context

    raw = await fetch_points_with_vectors(document_id, limit=limit, layer=layer)
    ctx = await get_l4_clustering_context(document_id=document_id)
    empty = {
        "document_id": document_id,
        "total": 0,
        "l4_total": 0,
        "cluster_count": 0,
        "anomaly_count": 0,
        "has_clusters": False,
        "has_named_clusters": False,
        "method": "pca",
        "layer_filter": layer,
        "clusters": [],
        "points": [],
        "clustering_context": ctx,
    }
    if not raw:
        return empty
    vectors = [p["vector"] for p in raw]
    coords = _pca_to_2d(vectors)
    has_clusters = any(
        p.get("layer") == "L4" and p.get("cluster_id") is not None
        for p in raw
    )
    has_named_clusters = any(
        p.get("layer") == "L4"
        and p.get("cluster_id") is not None
        and int(p["cluster_id"]) >= 0
        for p in raw
    )
    cluster_meta: dict[int, dict[str, Any]] = {}
    points: list[dict[str, Any]] = []
    anomaly_count = 0
    for p, (x, y) in zip(raw, coords):
        cid = p.get("cluster_id")
        cname = p.get("cluster_name")
        cdesc = p.get("cluster_description")
        is_l4 = p.get("layer") == "L4"
        is_anomaly = bool(p.get("is_anomaly")) or (is_l4 and cid is not None and int(cid) < 0)
        if is_l4 and is_anomaly:
            anomaly_count += 1
        if is_l4 and cid is not None and int(cid) >= 0:
            cid_int = int(cid)
            bucket = cluster_meta.setdefault(
                cid_int,
                {"id": cid_int, "name": cname or f"Кластер {cid_int}", "count": 0, "description": cdesc},
            )
            if cname:
                bucket["name"] = cname
            if cdesc:
                bucket["description"] = cdesc
            bucket["count"] += 1
        points.append(
            {
                "id": p["id"],
                "x": round(x, 6),
                "y": round(y, 6),
                "layer": p.get("layer"),
                "cluster_id": cid,
                "cluster_name": cname,
                "cluster_description": cdesc,
                "is_anomaly": is_anomaly if is_l4 else p.get("is_anomaly"),
                "anomaly_reason": p.get("anomaly_reason"),
                "anomaly_score": p.get("anomaly_score"),
                "label": p.get("label"),
                "node_id": p.get("node_id"),
                "neo4j_node_id": p.get("neo4j_node_id"),
                "text": p.get("text"),
                "document_id": p.get("document_id"),
                "collection": p.get("collection"),
            }
        )
    palette = [
        "#ef6c00", "#7b1fa2", "#1565c0", "#2e7d32", "#00838f",
        "#6a1b9a", "#558b2f", "#ad1457", "#4527a0", "#fb8c00",
    ]
    clusters_out = []
    for cid in sorted(cluster_meta):
        info = cluster_meta[cid]
        clusters_out.append({
            "id": info["id"],
            "name": info["name"] or f"Кластер {info['id']}",
            "count": info["count"],
            "color": palette[abs(cid) % len(palette)],
            "description": info.get("description"),
        })
    l4_total = sum(1 for p in raw if p.get("layer") == "L4")
    return {
        "document_id": document_id,
        "total": len(points),
        "l4_total": l4_total,
        "cluster_count": len(clusters_out),
        "anomaly_count": anomaly_count,
        "has_clusters": has_clusters,
        "has_named_clusters": has_named_clusters,
        "method": "pca",
        "layer_filter": layer,
        "clusters": clusters_out,
        "points": points,
        "clustering_context": ctx,
    }
