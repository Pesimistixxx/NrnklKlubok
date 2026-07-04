"""API аномалий L4: кластеризация HDBSCAN и список выбросов."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from mkg_core.embeddings import index_document_graph
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.l4_clustering import (
    apply_global_l4_cluster,
    get_cluster_detail,
    get_l4_point_detail,
    list_anomalies_from_graph,
)

from app.schemas import (
    AnomalyNodeOut,
    AnomaliesListOut,
    L4ClusterDetailOut,
    L4ClusterOut,
    L4ClusterRequest,
    L4PointDetailOut,
)
from app.storage import get_repo

router = APIRouter(prefix="/graph", tags=["graph-anomalies"])


def _normalize_doc_id(doc_id: str) -> str:
    doc_id = (doc_id or "").strip()
    if doc_id.startswith("doc_") and ":" not in doc_id:
        return f"doc:{doc_id[4:]}"
    return doc_id


def _load_graph(doc_id: str, *, required: bool = True) -> dict[str, Any]:
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


@router.post("/l4/cluster", response_model=L4ClusterOut)
async def post_l4_cluster(body: L4ClusterRequest) -> L4ClusterOut:
    """Глобальный HDBSCAN по всем L4-векторам Qdrant → cluster_id / is_anomaly / cluster_name."""
    doc_id = _normalize_doc_id(body.document_id) if body.document_id else None
    if doc_id:
        rec = get_repo().get(doc_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Документ не найден")
        graph = _load_graph(doc_id)
        if graph.get("nodes"):
            await index_document_graph(doc_id, graph)

    try:
        stats = await apply_global_l4_cluster(doc_id, force=True, min_cluster_size=body.min_cluster_size)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return L4ClusterOut(**stats)


@router.get("/l4/cluster/{cluster_id}/detail", response_model=L4ClusterDetailOut)
async def get_l4_cluster_detail(
    cluster_id: int,
    document_id: str | None = Query(None, description="Фильтр по документу"),
) -> L4ClusterDetailOut:
    """Описание кластера L4, участники и связи Neo4j."""
    doc_id = _normalize_doc_id(document_id) if document_id else None
    if doc_id and not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    try:
        raw = await get_cluster_detail(cluster_id, document_id=doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return L4ClusterDetailOut(**raw)


@router.get("/l4/point/{node_id}/detail", response_model=L4PointDetailOut)
async def get_l4_point_detail_endpoint(
    node_id: str,
    document_id: str | None = Query(None, description="Фильтр по документу"),
) -> L4PointDetailOut:
    """Детали L4-точки: текст, причина аномалии, ближайший кластер."""
    doc_id = _normalize_doc_id(document_id) if document_id else None
    if doc_id and not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    try:
        raw = await get_l4_point_detail(node_id, document_id=doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return L4PointDetailOut(**raw)


@router.get("/anomalies", response_model=AnomaliesListOut)
async def get_anomalies(
    document_id: str | None = Query(None, description="Фильтр по документу"),
    limit: int = Query(100, ge=1, le=500),
    auto_cluster: bool = Query(
        True,
        description="Запустить кластеризацию, если меток аномалий ещё нет",
    ),
) -> AnomaliesListOut:
    """Список L4-узлов-аномалий (is_anomaly / cluster_id=-1)."""
    items: list[dict[str, Any]] = []
    doc_ids: list[str] = []

    if document_id:
        rec = get_repo().get(document_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Документ не найден")
        doc_ids = [document_id]
    else:
        raw_items, _ = get_repo().list(1, 500)
        doc_ids = [r["id"] for r in raw_items if (r.get("graph_nodes") or 0) > 0]

    for doc_id in doc_ids:
        graph = _load_graph(doc_id, required=False)
        if not graph.get("nodes"):
            continue
        existing = list_anomalies_from_graph(graph, document_id=doc_id, limit=1)
        if auto_cluster and not existing:
            try:
                await index_document_graph(doc_id, graph)
                await apply_global_l4_cluster(doc_id, force=True)
                graph = _load_graph(doc_id, required=False)
            except Exception:
                pass
        items.extend(list_anomalies_from_graph(graph, document_id=doc_id, limit=limit))

    items.sort(
        key=lambda x: (
            -(float(x.get("anomaly_score") or 0)),
            str(x.get("document_id")),
            str(x.get("node_id")),
        ),
    )
    trimmed = items[:limit]
    return AnomaliesListOut(
        total=len(trimmed),
        document_id=document_id,
        items=[AnomalyNodeOut(**item) for item in trimmed],
    )
