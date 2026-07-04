"""HDBSCAN-кластеризация L4-узлов по векторам Qdrant."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from qdrant_client.models import FieldCondition, Filter, MatchValue

from mkg_core.config import get_settings
from mkg_core.neo4j_client import Neo4jClient
from mkg_core.qdrant import QdrantClientSingleton
from mkg_core.store import get_repo

log = logging.getLogger(__name__)

try:
    import hdbscan
except Exception:  # pragma: no cover
    hdbscan = None

_L4_LABELS = frozenset(
    {
        "ExperimentRun",
        "TechStage",
        "Measurement",
        "Deviation",
        "TrendVector",
        "Formula",
        "EnvironmentalCondition",
        "Effect",
        "Claim",
    }
)


async def fetch_l4_vectors(
    *,
    document_id: str | None = None,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    """Scroll Qdrant mkg_claims — L4 точки с векторами."""
    settings = get_settings()
    qdrant = QdrantClientSingleton.instance().client
    filt_must = [FieldCondition(key="layer", match=MatchValue(value="L4"))]
    if document_id:
        filt_must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
    scroll_filter = Filter(must=filt_must)

    out: list[dict[str, Any]] = []
    offset = None
    while len(out) < limit:
        batch_limit = min(128, limit - len(out))
        records, offset = await qdrant.scroll(
            collection_name=settings.qdrant_collection_claims,
            scroll_filter=scroll_filter,
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
                    "point_id": str(rec.id),
                    "node_id": str(payload.get("node_id") or payload.get("neo4j_node_id") or ""),
                    "neo4j_node_id": str(payload.get("neo4j_node_id") or payload.get("node_id") or ""),
                    "document_id": str(payload.get("document_id") or ""),
                    "label": str(payload.get("label") or ""),
                    "vector": list(vector),
                }
            )
        if offset is None or not records:
            break
    return out


def cluster_vectors(
    vectors: np.ndarray,
    *,
    min_cluster_size: int,
    min_samples: int | None,
) -> tuple[list[int], list[float]]:
    if hdbscan is None:
        raise RuntimeError("hdbscan не установлен: pip install hdbscan")
    if len(vectors) == 0:
        return [], []
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        prediction_data=True,
    )
    labels = clusterer.fit_predict(vectors)
    outlier = getattr(clusterer, "outlier_scores_", np.zeros(len(vectors)))
    outlier = np.nan_to_num(outlier, nan=0.0)
    return [int(x) for x in labels], [float(x) for x in outlier]


async def _write_neo4j_labels(node_id: str, label: str, cluster_id: int, anomaly_score: float) -> None:
    if not node_id or label not in _L4_LABELS:
        return
    is_anomaly = cluster_id == -1
    client = Neo4jClient.instance()
    cypher = f"""
    MATCH (n:{label} {{id: $id}})
    SET n.cluster_id = $cluster_id,
        n.anomaly_score = $anomaly_score,
        n.is_anomaly = $is_anomaly
    RETURN n.id AS id
    """
    try:
        await client.run_write(
            cypher,
            {
                "id": node_id,
                "cluster_id": cluster_id,
                "anomaly_score": anomaly_score,
                "is_anomaly": is_anomaly,
            },
        )
    except Exception as exc:
        log.warning("neo4j cluster label failed node=%s: %s", node_id, exc)


def _update_local_graph(doc_id: str, node_id: str, cluster_id: int, anomaly_score: float) -> bool:
    repo = get_repo()
    graph = repo.read_graph(doc_id)
    if not graph:
        return False
    changed = False
    for node in graph.get("nodes") or []:
        if str(node.get("id")) != node_id:
            continue
        props = dict(node.get("props") or {})
        props["cluster_id"] = cluster_id
        props["anomaly_score"] = round(anomaly_score, 4)
        props["is_anomaly"] = cluster_id == -1
        node["props"] = props
        changed = True
        break
    if changed:
        repo.save_graph(doc_id, graph)
    return changed


async def run_l4_clustering(
    *,
    document_id: str | None = None,
    min_cluster_size: int | None = None,
    min_samples: int | None = None,
    limit: int = 5000,
) -> dict[str, Any]:
    """HDBSCAN по L4-векторам Qdrant → метки в Neo4j, JSON-графах и payload Qdrant."""
    settings = get_settings()
    mcs = min_cluster_size if min_cluster_size is not None else settings.hdbscan_min_cluster_size
    ms = min_samples if min_samples is not None else settings.hdbscan_min_samples

    points = await fetch_l4_vectors(document_id=document_id, limit=limit)
    if len(points) < max(2, mcs):
        return {
            "clustered": 0,
            "anomalies": 0,
            "points": len(points),
            "clusters": 0,
            "message": f"Недостаточно L4-точек для HDBSCAN (нужно ≥{mcs}, есть {len(points)})",
        }

    vectors = np.array([p["vector"] for p in points], dtype=np.float64)
    labels, scores = cluster_vectors(vectors, min_cluster_size=mcs, min_samples=ms)

    qdrant = QdrantClientSingleton.instance().client
    clustered = 0
    anomalies = 0
    cluster_ids: set[int] = set()

    for point, cluster_id, score in zip(points, labels, scores):
        node_id = point["neo4j_node_id"] or point["node_id"]
        doc_id = point["document_id"]
        node_label = point["label"]
        if not node_id:
            continue
        cluster_ids.add(cluster_id)
        if cluster_id == -1:
            anomalies += 1
        clustered += 1

        if doc_id:
            _update_local_graph(doc_id, node_id, cluster_id, score)
        await _write_neo4j_labels(node_id, node_label, cluster_id, score)

        try:
            await qdrant.set_payload(
                collection_name=settings.qdrant_collection_claims,
                payload={
                    "cluster_id": cluster_id,
                    "anomaly_score": round(score, 4),
                    "is_anomaly": cluster_id == -1,
                    "neo4j_node_id": node_id,
                },
                points=[point["point_id"]],
            )
        except Exception as exc:
            log.warning("qdrant set_payload failed point=%s: %s", point["point_id"], exc)

    valid_clusters = {c for c in cluster_ids if c >= 0}
    return {
        "clustered": clustered,
        "anomalies": anomalies,
        "points": len(points),
        "clusters": len(valid_clusters),
        "document_id": document_id,
        "min_cluster_size": mcs,
    }


def _node_text(node: dict[str, Any]) -> str:
    props = node.get("props") or {}
    for key in ("raw_text_ru", "quote", "text", "name_ru", "title_ru", "value", "name", "statement"):
        val = props.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _anomaly_reason(props: dict[str, Any], cluster_id: int | None) -> str:
    if props.get("anomaly_reason"):
        return str(props["anomaly_reason"])
    if cluster_id == -1:
        return "hdbscan_noise"
    if props.get("is_anomaly"):
        return "flagged_anomaly"
    return "unknown"


def _l4_nodes_in_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        n for n in (graph.get("nodes") or [])
        if str(n.get("label") or "") in _L4_LABELS
    ]


def list_anomalies_from_graph(
    graph: dict[str, Any],
    *,
    document_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """L4-узлы с is_anomaly или cluster_id=-1 из локального graph payload."""
    items: list[dict[str, Any]] = []
    for node in _l4_nodes_in_graph(graph):
        props = dict(node.get("props") or {})
        cluster_id = props.get("cluster_id", props.get("l4_cluster"))
        is_anom = props.get("is_anomaly") is True or cluster_id == -1
        if not is_anom:
            continue
        node_id = str(node.get("id") or "")
        text = str(props.get("text_ru") or props.get("title_ru") or props.get("quote") or _node_text(node))[:400]
        reason = "HDBSCAN outlier (cluster=-1)" if cluster_id == -1 else "is_anomaly"
        items.append(
            {
                "document_id": document_id,
                "node_id": node_id,
                "label": str(node.get("label") or ""),
                "layer": "L4",
                "text": text,
                "cluster_id": int(cluster_id) if cluster_id is not None else -1,
                "anomaly_score": props.get("anomaly_score"),
                "is_anomaly": True,
                "anomaly_reason": reason,
                "props": props,
            }
        )
        if len(items) >= limit:
            break
    items.sort(
        key=lambda x: (-(float(x.get("anomaly_score") or 0)), str(x.get("node_id"))),
    )
    return items[:limit]


async def cluster_document_l4(
    document_id: str,
    graph: dict[str, Any],
    *,
    min_cluster_size: int | None = None,
    index_if_missing: bool = True,
) -> dict[str, Any]:
    """HDBSCAN для одного документа: опционально индексирует L4, обновляет graph in-place."""
    from mkg_core.embeddings import count_indexed_points, index_document_graph

    l4_nodes = _l4_nodes_in_graph(graph)
    if index_if_missing and l4_nodes:
        counts = await count_indexed_points(document_id=document_id)
        if not counts.get(get_settings().qdrant_collection_claims):
            await index_document_graph(document_id, graph)

    stats = await run_l4_clustering(
        document_id=document_id,
        min_cluster_size=min_cluster_size,
    )
    fresh = get_repo().read_graph(document_id) or graph
    graph.clear()
    graph.update(fresh)

    structural = sum(
        1 for n in l4_nodes
        if not (n.get("props") or {}).get("text_ru") and not (n.get("props") or {}).get("title_ru")
    )
    hdbscan_anomalies = int(stats.get("anomalies") or 0)
    return {
        "document_id": document_id,
        "l4_nodes": len(l4_nodes),
        "vectors_found": int(stats.get("points") or 0),
        "clustered": int(stats.get("clustered") or 0),
        "hdbscan_anomalies": hdbscan_anomalies,
        "structural_anomalies": structural,
        "total_anomalies": hdbscan_anomalies + structural,
    }


async def apply_document_l4_cluster(document_id: str) -> dict[str, Any]:
    """HDBSCAN L4 после Qdrant: метки в граф/Neo4j и поля в registry."""
    from mkg_core.meta_db import update_document_status
    from mkg_core.store import get_repo

    repo = get_repo()
    rec = repo.get(document_id) or {}
    if rec.get("processing_mode") == "answers_only":
        return {"skipped": True, "reason": "answers_only", "document_id": document_id}

    status = rec.get("status") or "loaded"
    repo.set_status(document_id, status, step="l4_cluster", l4_error=None)
    try:
        await update_document_status(document_id, status, step="l4_cluster", l4_error=None)
    except Exception as exc:
        log.warning("postgres update failed l4_cluster start doc_id=%s: %s", document_id, exc)

    try:
        stats = await run_l4_clustering(document_id=document_id)
        extra = {
            "l4_clusters": int(stats.get("clusters") or 0),
            "l4_anomalies": int(stats.get("anomalies") or 0),
            "l4_clustered": int(stats.get("clustered") or 0),
            "l4_points": int(stats.get("points") or 0),
            "step": "l4_done",
            "l4_error": None,
        }
        repo.set_status(document_id, status, **extra)
        try:
            await update_document_status(document_id, status, **extra)
        except Exception as exc:
            log.warning("postgres update failed l4_done doc_id=%s: %s", document_id, exc)
        log.info(
            "l4 cluster done doc_id=%s clusters=%s anomalies=%s",
            document_id,
            extra["l4_clusters"],
            extra["l4_anomalies"],
        )
        return {**stats, **extra}
    except Exception as exc:
        log.warning("l4 cluster failed doc_id=%s: %s", document_id, exc)
        repo.set_status(document_id, status, step="l4_failed", l4_error=str(exc))
        try:
            await update_document_status(document_id, status, step="l4_failed", l4_error=str(exc))
        except Exception:
            pass
        return {"document_id": document_id, "error": str(exc), "step": "l4_failed"}
