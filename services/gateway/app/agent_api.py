"""Agent-facing REST API — доступ к 6 слоям онтологии, графу и поиску.

Префикс: ``/api/v1/agents/``. Предназначен для LLM-агентов и внешних интеграций.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from mkg_core.annotated_md import _LABEL_LAYER, _LAYER_TITLES, inject_l3_markers
from mkg_core.embeddings import (
    embedding_status,
    index_document_graph,
    list_all_indexed_points,
    list_indexed_points,
    search_document,
)
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.layer_pipeline import LAYER_ORDER, L5_LABELS, build_layer_pipeline
from mkg_core.ontology import ALL_REL_TYPES

from app.schemas import (
    AgentCapabilitiesOut,
    AgentCapabilityOut,
    AgentDocListOut,
    AgentDocSummaryOut,
    AgentEmbeddingStatusOut,
    AgentEndpointOut,
    AgentGraphOut,
    AgentLayerDetailOut,
    AgentNodeDetailOut,
    AgentNodesListOut,
    AgentOntologyOut,
    AgentParagraphOut,
    AgentParagraphsOut,
    AgentQdrantPointOut,
    AgentQdrantPointsOut,
    AgentRelationshipsOut,
    AgentSearchOut,
    AgentSearchRequest,
    AgentTextOut,
    GraphNode,
    GraphRelationship,
    LayerPipelineOut,
)
from app.storage import get_repo

router = APIRouter(prefix="/agents", tags=["agents"])

# Типы связей из канонической онтологии MKG (единый источник правды).
_ONTOLOGY_REL_TYPES = sorted(ALL_REL_TYPES)


def _node_layer(node: dict[str, Any]) -> str:
    label = str(node.get("label") or "?")
    if label in L5_LABELS:
        return "L5"
    return _LABEL_LAYER.get(label, "L?")


def _require_doc(doc_id: str) -> dict[str, Any]:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return rec


def _load_graph(doc_id: str, *, required: bool = False) -> dict[str, Any]:
    payload = get_repo().read_graph(doc_id)
    if not payload:
        if required:
            raise HTTPException(status_code=404, detail="Граф ещё не сформирован")
        return {"nodes": [], "relationships": []}
    return dedupe_graph_payload(
        GraphPayload(
            nodes=list(payload.get("nodes") or []),
            relationships=list(payload.get("relationships") or []),
        )
    ).as_dict()


def _graph_to_out(doc_id: str, graph: dict[str, Any]) -> AgentGraphOut:
    nodes = [GraphNode(**n) for n in graph.get("nodes", [])]
    relationships = [
        GraphRelationship(
            type=r.get("type", ""),
            from_=r.get("from", ""),
            to=r.get("to", ""),
            props=r.get("props", {}),
        )
        for r in graph.get("relationships", [])
    ]
    return AgentGraphOut(document_id=doc_id, nodes=nodes, relationships=relationships)


def _layer_counts(graph: dict[str, Any]) -> dict[str, int]:
    counts = {layer: 0 for layer in LAYER_ORDER}
    for node in graph.get("nodes") or []:
        layer = _node_layer(node)
        if layer in counts:
            counts[layer] += 1
    return counts


def _node_text(node: dict[str, Any]) -> str:
    props = node.get("props") or {}
    for key in ("raw_text_ru", "quote", "text", "name_ru", "title_ru", "value", "name"):
        val = props.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _filter_graph(
    graph: dict[str, Any],
    *,
    layer: str | None = None,
    label: str | None = None,
    rel_type: str | None = None,
) -> dict[str, Any]:
    nodes = graph.get("nodes") or []
    rels = graph.get("relationships") or []
    node_by_id = {str(n.get("id")): n for n in nodes if n.get("id")}

    if layer or label:
        filtered_nodes = []
        for node in nodes:
            if layer and _node_layer(node) != layer:
                continue
            if label and str(node.get("label")) != label:
                continue
            filtered_nodes.append(node)
        keep_ids = {str(n.get("id")) for n in filtered_nodes}
        filtered_rels = [
            r
            for r in rels
            if str(r.get("from")) in keep_ids and str(r.get("to")) in keep_ids
        ]
        if rel_type:
            filtered_rels = [r for r in filtered_rels if str(r.get("type")) == rel_type]
        return {"nodes": filtered_nodes, "relationships": filtered_rels}

    if rel_type:
        filtered_rels = [r for r in rels if str(r.get("type")) == rel_type]
        keep_ids: set[str] = set()
        for r in filtered_rels:
            keep_ids.add(str(r.get("from")))
            keep_ids.add(str(r.get("to")))
        filtered_nodes = [node_by_id[nid] for nid in keep_ids if nid in node_by_id]
        return {"nodes": filtered_nodes, "relationships": filtered_rels}

    return graph


def _paragraphs_from_graph(graph: dict[str, Any], doc_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for node in graph.get("nodes") or []:
        if str(node.get("label")) != "TextParagraph":
            continue
        node_id = str(node.get("id") or "")
        text = _node_text(node)
        m = re.search(r":p:(\d+)$", node_id)
        index = int(m.group(1)) if m else len(items)
        items.append(
            {
                "node_id": node_id,
                "index": index,
                "text": text,
                "char_start": (node.get("props") or {}).get("char_start"),
                "char_end": (node.get("props") or {}).get("char_end"),
            }
        )
    items.sort(key=lambda x: x["index"])
    return items


def _paragraphs_from_md(doc_id: str, md: str) -> list[dict[str, Any]]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", md.strip()) if b.strip()]
    return [
        {
            "node_id": f"{doc_id}:p:{idx}",
            "index": idx,
            "text": block,
            "char_start": None,
            "char_end": None,
        }
        for idx, block in enumerate(blocks)
    ]


@router.get(
    "/docs",
    response_model=AgentDocListOut,
    summary="Список документов со статистикой по слоям",
)
async def list_agent_docs(page: int = 1, page_size: int = 50) -> AgentDocListOut:
    """Все документы с краткой сводкой L1–L6 (число узлов на слой)."""
    items_raw, total = get_repo().list(page, page_size)
    items: list[AgentDocSummaryOut] = []
    for rec in items_raw:
        doc_id = rec["id"]
        graph = _load_graph(doc_id)
        pipeline = build_layer_pipeline(
            doc_status=rec.get("status"),
            step=rec.get("step"),
            graph=graph if graph.get("nodes") else None,
            md_ready=bool(get_repo().read_markdown(doc_id)),
        )
        items.append(
            AgentDocSummaryOut(
                id=doc_id,
                file_name=rec.get("file_name", ""),
                status=rec.get("status", "uploaded"),
                step=rec.get("step"),
                layer_counts=_layer_counts(graph),
                total_nodes=pipeline["total_nodes"],
                total_relationships=pipeline["total_relationships"],
                layers=pipeline["layers"],
            )
        )
    return AgentDocListOut(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/documents/{doc_id}",
    response_model=AgentDocSummaryOut,
    summary="Метаданные документа и сводка по слоям",
)
async def get_agent_document(doc_id: str) -> AgentDocSummaryOut:
    """Статус документа, ошибки, counts L1–L6."""
    rec = _require_doc(doc_id)
    graph = _load_graph(doc_id)
    md = get_repo().read_markdown(doc_id)
    pipeline = build_layer_pipeline(
        doc_status=rec.get("status"),
        step=rec.get("step"),
        graph=graph if graph.get("nodes") else None,
        md_ready=bool(md and md.strip()),
    )
    return AgentDocSummaryOut(
        id=doc_id,
        file_name=rec.get("file_name", ""),
        status=rec.get("status", "uploaded"),
        step=rec.get("step"),
        error=rec.get("error") or rec.get("neo4j_error"),
        neo4j_synced=rec.get("neo4j_synced"),
        layer_counts=_layer_counts(graph),
        total_nodes=pipeline["total_nodes"],
        total_relationships=pipeline["total_relationships"],
        layers=pipeline["layers"],
    )


@router.get(
    "/documents/{doc_id}/layers",
    response_model=LayerPipelineOut,
    summary="Полный пайплайн слоёв L1–L6",
)
async def get_agent_layers(doc_id: str) -> LayerPipelineOut:
    """Статус каждого слоя, число узлов/связей, примеры связей."""
    rec = _require_doc(doc_id)
    graph = get_repo().read_graph(doc_id)
    md = get_repo().read_markdown(doc_id)
    payload = build_layer_pipeline(
        doc_status=rec.get("status"),
        step=rec.get("step"),
        graph=graph,
        md_ready=bool(md and md.strip()),
    )
    return LayerPipelineOut(**payload)


@router.get(
    "/documents/{doc_id}/layers/{layer_id}",
    response_model=AgentLayerDetailOut,
    summary="Узлы и связи одного слоя (L1–L6)",
)
async def get_agent_layer_detail(
    doc_id: str,
    layer_id: str,
    label: str | None = Query(None, description="Фильтр по label узла"),
) -> AgentLayerDetailOut:
    """Все узлы и связи слоя; опциональный фильтр по Neo4j label."""
    if layer_id not in LAYER_ORDER:
        raise HTTPException(status_code=400, detail=f"layer_id должен быть одним из {LAYER_ORDER}")
    _require_doc(doc_id)
    graph = _load_graph(doc_id, required=True)
    filtered = _filter_graph(graph, layer=layer_id, label=label)
    return AgentLayerDetailOut(
        document_id=doc_id,
        layer_id=layer_id,
        title=_LAYER_TITLES.get(layer_id, layer_id),
        nodes=[GraphNode(**n) for n in filtered["nodes"]],
        relationships=[
            GraphRelationship(
                type=r.get("type", ""),
                from_=r.get("from", ""),
                to=r.get("to", ""),
                props=r.get("props", {}),
            )
            for r in filtered["relationships"]
        ],
        node_count=len(filtered["nodes"]),
        relationship_count=len(filtered["relationships"]),
    )


@router.get(
    "/documents/{doc_id}/graph",
    response_model=AgentGraphOut,
    summary="Полный граф документа с фильтрами",
)
async def get_agent_graph(
    doc_id: str,
    layer: str | None = Query(None, description="Фильтр L1–L6"),
    label: str | None = Query(None, description="Фильтр label узла"),
    rel_type: str | None = Query(None, description="Фильтр типа связи"),
) -> AgentGraphOut:
    """Граф документа; query-параметры сужают узлы и связи."""
    _require_doc(doc_id)
    graph = _load_graph(doc_id, required=True)
    filtered = _filter_graph(graph, layer=layer, label=label, rel_type=rel_type)
    return _graph_to_out(doc_id, filtered)


@router.get(
    "/documents/{doc_id}/relationships",
    response_model=AgentRelationshipsOut,
    summary="Все связи документа",
)
async def get_agent_relationships(
    doc_id: str,
    rel_type: str | None = Query(None),
    layer: str | None = Query(None, description="Слой исходного узла (from)"),
) -> AgentRelationshipsOut:
    """Список связей с опциональным фильтром по типу и слою."""
    _require_doc(doc_id)
    graph = _load_graph(doc_id, required=True)
    rels = graph.get("relationships") or []
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or []}

    if layer:
        rels = [
            r
            for r in rels
            if _node_layer(node_by_id.get(str(r.get("from")), {})) == layer
        ]
    if rel_type:
        rels = [r for r in rels if str(r.get("type")) == rel_type]

    return AgentRelationshipsOut(
        document_id=doc_id,
        total=len(rels),
        relationships=[
            GraphRelationship(
                type=r.get("type", ""),
                from_=r.get("from", ""),
                to=r.get("to", ""),
                props=r.get("props", {}),
            )
            for r in rels
        ],
    )


@router.get(
    "/documents/{doc_id}/nodes",
    response_model=AgentNodesListOut,
    summary="Поиск узлов по id, имени, цитате",
)
async def list_agent_nodes(
    doc_id: str,
    q: str | None = Query(None, description="Keyword: id, name_ru, quote, title…"),
    label: str | None = Query(None, description="Neo4j label узла"),
    layer: str | None = Query(None, description="Слой L1–L6"),
    limit: int = Query(50, ge=1, le=500),
) -> AgentNodesListOut:
    """Список узлов документа с фильтрами по тексту, label и слою."""
    if layer and layer not in LAYER_ORDER:
        raise HTTPException(status_code=400, detail=f"layer должен быть одним из {LAYER_ORDER}")
    _require_doc(doc_id)
    graph = _load_graph(doc_id, required=True)
    nodes = graph.get("nodes") or []
    needle = (q or "").strip().lower()

    matched: list[dict[str, Any]] = []
    for node in nodes:
        if label and str(node.get("label")) != label:
            continue
        if layer and _node_layer(node) != layer:
            continue
        if needle:
            props = node.get("props") or {}
            haystack = " ".join(
                str(v)
                for v in [node.get("id"), node.get("label"), *props.values()]
                if v is not None
            ).lower()
            if needle not in haystack:
                continue
        matched.append(node)
        if len(matched) >= limit:
            break

    return AgentNodesListOut(
        document_id=doc_id,
        total=len(matched),
        query=q,
        layer=layer,
        label=label,
        nodes=[GraphNode(**n) for n in matched],
    )


@router.get(
    "/documents/{doc_id}/nodes/{node_id}",
    response_model=AgentNodeDetailOut,
    summary="Узел с соседями (incoming/outgoing)",
)
async def get_agent_node(doc_id: str, node_id: str) -> AgentNodeDetailOut:
    """Детали узла и все входящие/исходящие связи."""
    _require_doc(doc_id)
    graph = _load_graph(doc_id, required=True)
    node_by_id = {str(n.get("id")): n for n in graph.get("nodes") or []}
    node = node_by_id.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Узел не найден")

    incoming: list[GraphRelationship] = []
    outgoing: list[GraphRelationship] = []
    for r in graph.get("relationships") or []:
        if str(r.get("to")) == node_id:
            incoming.append(
                GraphRelationship(
                    type=r.get("type", ""),
                    from_=r.get("from", ""),
                    to=r.get("to", ""),
                    props=r.get("props", {}),
                )
            )
        if str(r.get("from")) == node_id:
            outgoing.append(
                GraphRelationship(
                    type=r.get("type", ""),
                    from_=r.get("from", ""),
                    to=r.get("to", ""),
                    props=r.get("props", {}),
                )
            )

    neighbors: list[GraphNode] = []
    seen: set[str] = set()
    for rel in incoming + outgoing:
        for nid in (rel.from_, rel.to):
            if nid != node_id and nid not in seen and nid in node_by_id:
                neighbors.append(GraphNode(**node_by_id[nid]))
                seen.add(nid)

    return AgentNodeDetailOut(
        document_id=doc_id,
        node=GraphNode(**node),
        layer=_node_layer(node),
        text=_node_text(node) or None,
        incoming=incoming,
        outgoing=outgoing,
        neighbors=neighbors,
    )


@router.get(
    "/documents/{doc_id}/text",
    response_model=AgentTextOut,
    summary="Markdown документа",
)
async def get_agent_text(
    doc_id: str,
    with_paragraph_index: bool = Query(False, description="Добавить L3 HTML-комментарии"),
) -> AgentTextOut:
    """Чистый markdown; опционально с L3-маркерами абзацев."""
    _require_doc(doc_id)
    md = get_repo().read_markdown(doc_id)
    if md is None:
        raise HTTPException(status_code=404, detail="Markdown ещё не готов")
    body = inject_l3_markers(doc_id, md) if with_paragraph_index else md
    paragraphs = _paragraphs_from_md(doc_id, md)
    return AgentTextOut(
        document_id=doc_id,
        markdown=body,
        paragraph_count=len(paragraphs),
        with_paragraph_index=with_paragraph_index,
    )


@router.get(
    "/documents/{doc_id}/paragraphs",
    response_model=AgentParagraphsOut,
    summary="L3 TextParagraph — список абзацев",
)
async def get_agent_paragraphs(doc_id: str) -> AgentParagraphsOut:
    """Абзацы L3 из графа (после extraction) или из markdown (до extraction)."""
    _require_doc(doc_id)
    graph = _load_graph(doc_id)
    md = get_repo().read_markdown(doc_id) or ""

    if graph.get("nodes"):
        raw = _paragraphs_from_graph(graph, doc_id)
        source = "graph"
    elif md.strip():
        raw = _paragraphs_from_md(doc_id, md)
        source = "markdown"
    else:
        raise HTTPException(status_code=404, detail="Текст документа недоступен")

    return AgentParagraphsOut(
        document_id=doc_id,
        source=source,
        total=len(raw),
        paragraphs=[AgentParagraphOut(**p) for p in raw],
    )


@router.post(
    "/documents/{doc_id}/search",
    response_model=AgentSearchOut,
    summary="Поиск по документу (semantic / keyword)",
)
async def agent_search(doc_id: str, body: AgentSearchRequest) -> AgentSearchOut:
    """Семантический поиск через Qdrant+Yandex embed; fallback — keyword по графу."""
    _require_doc(doc_id)
    graph = _load_graph(doc_id)
    if not graph.get("nodes") and not get_repo().read_markdown(doc_id):
        raise HTTPException(status_code=404, detail="Нет данных для поиска")

    result = await search_document(
        doc_id,
        graph if graph.get("nodes") else None,
        body.query,
        limit=body.limit,
        mode=body.mode,
        layers=body.layers,
        index_if_missing=body.index_if_missing,
    )
    return AgentSearchOut(
        document_id=doc_id,
        query=body.query,
        mode=result["mode"],
        hits=result["hits"],
        index=result.get("index"),
    )


@router.post(
    "/documents/{doc_id}/embeddings/index",
    summary="Проиндексировать TextParagraph и Claim в Qdrant",
)
async def agent_index_embeddings(doc_id: str) -> dict[str, Any]:
    """Явная индексация L3/L4 узлов в Qdrant (Yandex embeddings)."""
    _require_doc(doc_id)
    graph = _load_graph(doc_id, required=True)
    stats = await index_document_graph(doc_id, graph)
    return {"document_id": doc_id, **stats}


@router.get(
    "/ontology",
    response_model=AgentOntologyOut,
    summary="Определения слоёв L1–L6, labels и типы связей",
)
async def get_ontology() -> AgentOntologyOut:
    """Справочник онтологии для агентов: слои, node labels, relationship types."""
    labels_by_layer: dict[str, list[str]] = defaultdict(list)
    for label, layer in sorted(_LABEL_LAYER.items()):
        labels_by_layer[layer].append(label)

    layers = [
        {
            "id": layer_id,
            "title": _LAYER_TITLES.get(layer_id, layer_id),
            "node_labels": labels_by_layer.get(layer_id, []),
        }
        for layer_id in (*LAYER_ORDER, "L?")
        if labels_by_layer.get(layer_id)
    ]

    return AgentOntologyOut(
        layers=layers,
        node_labels=dict(_LABEL_LAYER),
        relationship_types=_ONTOLOGY_REL_TYPES,
    )


@router.get(
    "/embeddings/status",
    response_model=AgentEmbeddingStatusOut,
    summary="Статус эмбеддингов и Qdrant",
)
async def get_embeddings_status() -> AgentEmbeddingStatusOut:
    """Где хранятся вектора, модели Yandex, статистика коллекций Qdrant."""
    status = await embedding_status()
    return AgentEmbeddingStatusOut(**status)


@router.get(
    "/documents/{doc_id}/embeddings/points",
    response_model=AgentQdrantPointsOut,
    summary="Точки Qdrant документа (scroll, без векторов)",
)
async def get_document_qdrant_points(
    doc_id: str,
    collection: str | None = Query(None, description="mkg_chunks или mkg_claims"),
    limit: int = Query(100, ge=1, le=500),
) -> AgentQdrantPointsOut:
    """Список проиндексированных точек — аналог просмотра узлов Neo4j."""
    _require_doc(doc_id)
    raw = await list_indexed_points(doc_id, collection=collection, limit=limit)
    points = [AgentQdrantPointOut(**p) for p in raw]
    return AgentQdrantPointsOut(document_id=doc_id, total=len(points), points=points)


@router.get(
    "/embeddings/points/all",
    response_model=AgentQdrantPointsOut,
    summary="Все точки Qdrant (кластер / карта)",
)
async def get_all_qdrant_points(
    limit: int = Query(500, ge=1, le=2000),
) -> AgentQdrantPointsOut:
    raw = await list_all_indexed_points(limit=limit)
    points = [AgentQdrantPointOut(**p) for p in raw]
    return AgentQdrantPointsOut(document_id="__all__", total=len(points), points=points)


@router.get(
    "/capabilities",
    response_model=AgentCapabilitiesOut,
    summary="Реестр агентов MKG и доступные endpoint'ы",
)
async def get_agent_capabilities() -> AgentCapabilitiesOut:
    """8+ ролей из ТЗ с привязкой к REST API (для оркестраторов и LLM-агентов)."""
    base = "/api/v1/agents"
    agents = [
        AgentCapabilityOut(
            id="ingestion",
            name_ru="Агент приёма документов",
            layer_scope="L2/L3",
            implementation="worker.run_ingestion + gateway upload",
            endpoints=[
                AgentEndpointOut(method="POST", path="/api/v1/documents", summary="Загрузка файла", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/text", summary="Markdown документа", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/paragraphs", summary="L3 абзацы", status="ready"),
            ],
        ),
        AgentCapabilityOut(
            id="extraction",
            name_ru="Агент NLP-извлечения",
            layer_scope="L1–L6",
            implementation="worker.run_extraction + mkg_extraction",
            endpoints=[
                AgentEndpointOut(method="POST", path="/api/v1/documents/{id}/submit", summary="Запуск extraction", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/layers", summary="Пайплайн L1–L6", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/layers/{{L}}", summary="Узлы слоя", status="ready"),
            ],
        ),
        AgentCapabilityOut(
            id="graph_fusion",
            name_ru="Агент слияния графа",
            layer_scope="Neo4j",
            implementation="loader.load_graph MERGE",
            endpoints=[
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/graph", summary="Граф JSON", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/relationships", summary="Все связи", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/nodes", summary="Поиск узлов", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/nodes/{{node_id}}", summary="Узел + соседи", status="ready"),
            ],
        ),
        AgentCapabilityOut(
            id="retrieval",
            name_ru="Поисковый агент (Retrieval)",
            layer_scope="L3/L4 + Qdrant",
            implementation="embeddings.search_document",
            endpoints=[
                AgentEndpointOut(method="POST", path=f"{base}/documents/{{id}}/search", summary="Semantic/keyword", status="ready"),
                AgentEndpointOut(method="POST", path=f"{base}/documents/{{id}}/embeddings/index", summary="Индексация Qdrant", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/embeddings/points", summary="Точки Qdrant", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/embeddings/status", summary="Статус Qdrant", status="ready"),
            ],
        ),
        AgentCapabilityOut(
            id="validation",
            name_ru="Агент валидации",
            layer_scope="L5",
            implementation="analytics (скелет)",
            endpoints=[
                AgentEndpointOut(method="GET", path=f"{base}/ontology", summary="Онтология L5", status="ready"),
                AgentEndpointOut(method="GET", path="/api/v1/documents/{id}/pipeline/layers", summary="Статус слоёв", status="ready"),
            ],
        ),
        AgentCapabilityOut(
            id="synthesis",
            name_ru="Агент аналитики",
            layer_scope="L4/L6",
            implementation="planned RAG orchestrator",
            endpoints=[
                AgentEndpointOut(method="GET", path=f"{base}/docs", summary="Каталог документов", status="ready"),
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}", summary="Сводка документа", status="partial"),
            ],
        ),
        AgentCapabilityOut(
            id="security",
            name_ru="Агент безопасности",
            layer_scope="L5 SecurityRole",
            implementation="planned RBAC",
            endpoints=[
                AgentEndpointOut(method="GET", path=f"{base}/documents/{{id}}/layers/L5", summary="SecurityRole узлы", status="partial"),
            ],
        ),
        AgentCapabilityOut(
            id="notification",
            name_ru="Агент уведомлений",
            layer_scope="—",
            implementation="planned",
            endpoints=[
                AgentEndpointOut(method="GET", path="/api/v1/documents/{id}/logs", summary="Логи пайплайна", status="ready"),
            ],
        ),
    ]
    return AgentCapabilitiesOut(
        project_stage="MVP-2",
        stage_label_ru="Ingestion + Extraction + Neo4j + Qdrant search; validation/RAG — в работе",
        agents=agents,
    )
