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
from mkg_core.qdrant import QdrantClientSingleton

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
    if label == "Claim":
        return settings.qdrant_collection_claims
    return settings.qdrant_collection_chunks


def _indexable_labels() -> frozenset[str]:
    return frozenset({"TextParagraph", "Claim"})


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
        point = PointStruct(
            id=_point_id(node_id),
            vector=vector,
            payload={
                "document_id": document_id,
                "node_id": node_id,
                "label": label,
                "layer": _node_layer(node),
                "text": text[:2000],
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
                        "label": payload.get("label"),
                        "layer": payload.get("layer"),
                        "text": (payload.get("text") or "")[:300],
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


async def semantic_search(
    document_id: str,
    query: str,
    *,
    limit: int = 10,
    layers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Семантический поиск в Qdrant по эмбеддингу запроса."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return []

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    qdrant = QdrantClientSingleton.instance().client
    query_vector = await llm.embed(query, kind="query")

    doc_filter = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    hits: list[dict[str, Any]] = []

    for collection in (settings.qdrant_collection_chunks, settings.qdrant_collection_claims):
        try:
            results = await qdrant.search(
                collection_name=collection,
                query_vector=query_vector,
                query_filter=doc_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            log.warning("qdrant search %s: %s", collection, exc)
            continue
        for point in results:
            payload = point.payload or {}
            layer = str(payload.get("layer") or "L?")
            if layers and layer not in layers:
                continue
            hits.append(
                {
                    "node_id": str(payload.get("node_id") or ""),
                    "label": str(payload.get("label") or ""),
                    "layer": layer,
                    "score": float(point.score or 0),
                    "text": str(payload.get("text") or "")[:500],
                    "props": {},
                    "mode": "semantic",
                }
            )

    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]


async def semantic_search_global(
    query: str,
    *,
    limit: int = 10,
    layers: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Семантический поиск по всем документам (или по списку document_ids)."""
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return []

    await ensure_qdrant_collections()
    llm = YandexLLMClient.instance()
    qdrant = QdrantClientSingleton.instance().client
    query_vector = await llm.embed(query, kind="query")

    doc_filter: Filter | None = None
    if document_ids:
        doc_filter = Filter(
            must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))],
        )

    hits: list[dict[str, Any]] = []
    for collection in (settings.qdrant_collection_chunks, settings.qdrant_collection_claims):
        try:
            results = await qdrant.search(
                collection_name=collection,
                query_vector=query_vector,
                query_filter=doc_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            log.warning("qdrant global search %s: %s", collection, exc)
            continue
        for point in results:
            payload = point.payload or {}
            layer = str(payload.get("layer") or "L?")
            if layers and layer not in layers:
                continue
            hits.append(
                {
                    "node_id": str(payload.get("node_id") or ""),
                    "document_id": str(payload.get("document_id") or ""),
                    "label": str(payload.get("label") or ""),
                    "layer": layer,
                    "score": float(point.score or 0),
                    "text": str(payload.get("text") or "")[:500],
                    "props": {},
                    "mode": "semantic",
                }
            )

    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]


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
            semantic_hits = await semantic_search(document_id, query, limit=limit, layers=layers)
            if semantic_hits:
                used_mode = "semantic"

    if semantic_hits:
        return {"mode": used_mode, "hits": semantic_hits, "index": index_stats}

    if mode == "semantic" and not semantic_hits:
        used_mode = "keyword"

    kw_hits = keyword_search(graph or {}, query, limit=limit, layers=layers)
    return {"mode": used_mode if mode != "auto" else "keyword", "hits": kw_hits, "index": index_stats}


async def embedding_status() -> dict[str, Any]:
    """Где живут эмбеддинги и текущая статистика."""
    from mkg_core.runtime_config import get_emb_doc_model, get_emb_query_model, get_llm_model, get_ocr_model

    settings = get_settings()
    counts = await count_indexed_points()
    return {
        "provider": "yandex",
        "embed_doc_model": await get_emb_doc_model(),
        "embed_query_model": await get_emb_query_model(),
        "llm_model": await get_llm_model(),
        "ocr_model": await get_ocr_model(),
        "embed_client": "packages/core/src/mkg_core/llm.py::YandexLLMClient.embed",
        "qdrant_url": settings.qdrant_url,
        "collections": {
            settings.qdrant_collection_chunks: {
                "purpose": "L3 TextParagraph chunks",
                "points": counts.get(settings.qdrant_collection_chunks, 0),
            },
            settings.qdrant_collection_claims: {
                "purpose": "L4 Claim nodes",
                "points": counts.get(settings.qdrant_collection_claims, 0),
            },
        },
        "vector_size": settings.qdrant_vector_size,
        "yandex_configured": bool(settings.yandex_api_key and settings.yandex_folder_id),
        "auto_index_on_search": True,
        "pipeline_auto_index": False,
        "note": (
            "Extraction pipeline не пишет в Qdrant автоматически. "
            "Индексация при первом POST /agents/documents/{id}/search или вызове index_document_graph."
        ),
    }
