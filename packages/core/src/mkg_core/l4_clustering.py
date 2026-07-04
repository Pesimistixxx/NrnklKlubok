"""HDBSCAN-кластеризация L4-узлов по векторам Qdrant (глобально по всему корпусу)."""
from __future__ import annotations

import logging
import re
from collections import Counter
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

_RU_STOP = frozenset(
    {
        "и", "в", "во", "на", "для", "из", "что", "как", "при", "или", "не", "но",
        "от", "до", "по", "за", "об", "о", "the", "a", "an", "of", "in", "to", "for",
        "is", "are", "was", "with", "that", "this", "on", "at", "by", "from", "be",
        "был", "была", "были", "быть", "это", "так", "же", "также", "может", "можно",
        "the", "and", "or", "not", "all", "one", "two", "three",
    }
)

_CLUSTER_LOCK_KEY = "mkg:l4_global_cluster_lock"
_CLUSTER_DEBOUNCE_SECS = 30


async def fetch_l4_vectors(
    *,
    document_id: str | None = None,
    limit: int = 10000,
) -> list[dict[str, Any]]:
    """Scroll Qdrant mkg_claims — L4 точки с векторами. document_id — только фильтр viz."""
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
            text = str(payload.get("text") or "")[:400]
            out.append(
                {
                    "point_id": str(rec.id),
                    "node_id": str(payload.get("node_id") or payload.get("neo4j_node_id") or ""),
                    "neo4j_node_id": str(payload.get("neo4j_node_id") or payload.get("node_id") or ""),
                    "document_id": str(payload.get("document_id") or ""),
                    "label": str(payload.get("label") or ""),
                    "text": text,
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


def _heuristic_cluster_name(texts: list[str], cluster_id: int) -> str:
    words: Counter[str] = Counter()
    for text in texts:
        for w in re.findall(r"[\wа-яА-ЯёЁ]{3,}", text.lower()):
            if w not in _RU_STOP and not w.isdigit():
                words[w] += 1
    top = [w for w, _ in words.most_common(4)]
    if top:
        return " · ".join(top[:3]).capitalize()
    return f"Кластер {cluster_id}"


def _heuristic_cluster_description(texts: list[str], name: str) -> str:
    sample = " · ".join(t[:80] for t in texts[:3] if t.strip())
    if sample:
        return f"Группа связанных L4-фактов «{name}»: {sample[:220]}"
    return f"Тематическая группа L4-фактов «{name}»."


async def _llm_cluster_name(texts: list[str], heuristic: str) -> str:
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return heuristic
    try:
        from mkg_core.llm import YandexLLMClient

        sample = "\n".join(t for t in texts[:10] if t.strip())[:2000]
        if not sample.strip():
            return heuristic
        result = await YandexLLMClient.instance().generate(
            "Ты аналитик L4-слоя базы знаний MKG (утверждения, измерения, эффекты). "
            "Кластеры формирует HDBSCAN по эмбеддингам — твоя задача дать понятное имя группе фактов.",
            f"Примеры фактов кластера:\n{sample}\n\n"
            "Придумай короткое название (3–6 слов) на русском: тема или общий предмет. "
            "Только название, без кавычек и пояснений.",
            max_output_tokens=48,
            temperature=0.2,
        )
        name = result.strip().strip('"').strip("'").strip()[:80]
        return name or heuristic
    except Exception as exc:
        log.debug("llm cluster name failed: %s", exc)
        return heuristic


async def _llm_cluster_description(texts: list[str], name: str, heuristic: str) -> str:
    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return heuristic
    try:
        from mkg_core.llm import YandexLLMClient

        sample = "\n".join(t for t in texts[:12] if t.strip())[:2500]
        if not sample.strip():
            return heuristic
        result = await YandexLLMClient.instance().generate(
            "Ты аналитик L4-слоя MKG. Объясни пользователю, что объединяет кластер фактов, "
            "и какие связи между утверждениями можно ожидать в Neo4j.",
            f"Название кластера: {name}\n\nФакты:\n{sample}\n\n"
            "Напиши 2–3 предложения на русском: общая тема, типичные сущности, "
            "почему эти точки сгруппировались по смыслу. Без технических ID.",
            max_output_tokens=160,
            temperature=0.25,
        )
        desc = result.strip()[:600]
        return desc or heuristic
    except Exception as exc:
        log.debug("llm cluster description failed: %s", exc)
        return heuristic


async def generate_cluster_names(
    members_by_cluster: dict[int, list[str]],
    *,
    use_llm: bool | None = None,
) -> dict[int, str]:
    """Имена кластеров: эвристика по ключевым словам, опционально LLM."""
    meta = await generate_cluster_metadata(members_by_cluster, use_llm=use_llm)
    return {cid: info["name"] for cid, info in meta.items()}


async def generate_cluster_metadata(
    members_by_cluster: dict[int, list[str]],
    *,
    use_llm: bool | None = None,
) -> dict[int, dict[str, str]]:
    """Имена и описания кластеров для UI и Neo4j."""
    settings = get_settings()
    llm = use_llm if use_llm is not None else bool(settings.yandex_api_key)
    out: dict[int, dict[str, str]] = {}
    for cid in sorted(members_by_cluster):
        if cid < 0:
            continue
        texts = members_by_cluster[cid]
        heuristic_name = _heuristic_cluster_name(texts, cid)
        heuristic_desc = _heuristic_cluster_description(texts, heuristic_name)
        if llm and len(texts) >= 2:
            name = await _llm_cluster_name(texts, heuristic_name)
            desc = await _llm_cluster_description(texts, name, heuristic_desc)
        else:
            name, desc = heuristic_name, heuristic_desc
        out[cid] = {"name": name, "description": desc}
    return out


async def _write_neo4j_labels(
    node_id: str,
    label: str,
    cluster_id: int,
    anomaly_score: float,
    cluster_name: str | None = None,
    cluster_description: str | None = None,
    anomaly_reason: str | None = None,
) -> None:
    if not node_id or label not in _L4_LABELS:
        return
    is_anomaly = cluster_id == -1
    client = Neo4jClient.instance()
    cypher = f"""
    MATCH (n:{label} {{id: $id}})
    SET n.cluster_id = $cluster_id,
        n.anomaly_score = $anomaly_score,
        n.is_anomaly = $is_anomaly,
        n.cluster_name = $cluster_name,
        n.cluster_description = $cluster_description,
        n.anomaly_reason = $anomaly_reason
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
                "cluster_name": cluster_name or "",
                "cluster_description": cluster_description or "",
                "anomaly_reason": anomaly_reason or "",
            },
        )
    except Exception as exc:
        log.warning("neo4j cluster label failed node=%s: %s", node_id, exc)


def _update_local_graph(
    doc_id: str,
    node_id: str,
    cluster_id: int,
    anomaly_score: float,
    cluster_name: str | None = None,
    cluster_description: str | None = None,
    anomaly_reason: str | None = None,
) -> bool:
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
        if cluster_name:
            props["cluster_name"] = cluster_name
        if cluster_description:
            props["cluster_description"] = cluster_description
        if anomaly_reason:
            props["anomaly_reason"] = anomaly_reason
        node["props"] = props
        changed = True
        break
    if changed:
        repo.save_graph(doc_id, graph)
    return changed


async def _try_acquire_cluster_lock() -> bool:
    settings = get_settings()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        acquired = await r.set(_CLUSTER_LOCK_KEY, "1", nx=True, ex=_CLUSTER_DEBOUNCE_SECS)
        await r.aclose()
        return bool(acquired)
    except Exception as exc:
        log.debug("cluster lock unavailable: %s", exc)
        return True


def _update_all_documents_l4_status(stats: dict[str, Any]) -> None:
    """Обновить поля l4_* во всех документах registry после глобальной кластеризации."""
    repo = get_repo()
    per_doc: dict[str, dict[str, int]] = stats.get("per_document") or {}
    items, _ = repo.list(1, 500)
    global_clusters = int(stats.get("clusters") or 0)
    global_anomalies = int(stats.get("anomalies") or 0)
    global_clustered = int(stats.get("clustered") or 0)
    global_points = int(stats.get("points") or 0)
    for rec in items:
        doc_id = rec["id"]
        doc_stats = per_doc.get(doc_id, {})
        extra = {
            "l4_clusters": doc_stats.get("clusters", global_clusters),
            "l4_anomalies": doc_stats.get("anomalies", 0),
            "l4_clustered": doc_stats.get("clustered", 0),
            "l4_points": doc_stats.get("points", 0),
            "step": "l4_done",
            "l4_error": None,
        }
        if not doc_stats and global_clustered == 0:
            continue
        status = rec.get("status") or "loaded"
        repo.set_status(doc_id, status, **extra)


async def run_l4_clustering(
    *,
    document_id: str | None = None,
    min_cluster_size: int | None = None,
    min_samples: int | None = None,
    limit: int = 10000,
) -> dict[str, Any]:
    """HDBSCAN по всем L4-векторам Qdrant → метки в Neo4j, JSON-графах и payload Qdrant.

    document_id игнорируется для кластеризации (всегда глобально); оставлен для совместимости API.
    """
    _ = document_id  # viz-only filter elsewhere; clustering is always global
    settings = get_settings()
    mcs = min_cluster_size if min_cluster_size is not None else settings.hdbscan_min_cluster_size
    ms = min_samples if min_samples is not None else settings.hdbscan_min_samples

    points = await fetch_l4_vectors(document_id=None, limit=limit)
    if len(points) < max(2, mcs):
        return {
            "clustered": 0,
            "anomalies": 0,
            "points": len(points),
            "clusters": 0,
            "global": True,
            "cluster_names": {},
            "message": f"Недостаточно L4-точек для HDBSCAN (нужно ≥{mcs}, есть {len(points)})",
        }

    vectors = np.array([p["vector"] for p in points], dtype=np.float64)
    labels, scores = cluster_vectors(vectors, min_cluster_size=mcs, min_samples=ms)
    valid_clusters = {c for c in labels if c >= 0}
    used_min_samples = ms
    if not valid_clusters and len(points) >= max(2, mcs) and mcs <= 2:
        retry_ms = 1
        if ms != retry_ms:
            log.info("l4 cluster all-noise retry min_samples=%s (points=%s)", retry_ms, len(points))
            labels, scores = cluster_vectors(vectors, min_cluster_size=mcs, min_samples=retry_ms)
            used_min_samples = retry_ms
            valid_clusters = {c for c in labels if c >= 0}

    members_by_cluster: dict[int, list[str]] = {}
    for point, cluster_id in zip(points, labels):
        if cluster_id < 0:
            continue
        text = point.get("text") or point.get("node_id") or ""
        members_by_cluster.setdefault(cluster_id, []).append(str(text))

    cluster_meta = await generate_cluster_metadata(members_by_cluster)
    cluster_names = {cid: info["name"] for cid, info in cluster_meta.items()}
    cluster_descriptions = {cid: info["description"] for cid, info in cluster_meta.items()}

    qdrant = QdrantClientSingleton.instance().client
    clustered = 0
    anomalies = 0
    cluster_ids: set[int] = set()
    per_document: dict[str, dict[str, int]] = {}

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

        cname = cluster_names.get(cluster_id) if cluster_id >= 0 else None
        cdesc = cluster_descriptions.get(cluster_id) if cluster_id >= 0 else None
        reason = (
            "HDBSCAN: точка не попала ни в один плотный кластер (noise, cluster_id=-1). "
            "Эмбеддинг семантически далёк от других L4-фактов или корпус слишком мал/разрознен."
            if cluster_id == -1
            else None
        )

        if doc_id:
            _update_local_graph(doc_id, node_id, cluster_id, score, cname, cdesc, reason)
            bucket = per_document.setdefault(
                doc_id,
                {"clustered": 0, "anomalies": 0, "points": 0, "clusters": 0, "_cluster_ids": set()},
            )
            bucket["clustered"] += 1
            bucket["points"] += 1
            if cluster_id == -1:
                bucket["anomalies"] += 1
            if cluster_id >= 0:
                bucket["_cluster_ids"].add(cluster_id)

        await _write_neo4j_labels(node_id, node_label, cluster_id, score, cname, cdesc, reason)

        payload: dict[str, Any] = {
            "cluster_id": cluster_id,
            "anomaly_score": round(score, 4),
            "is_anomaly": cluster_id == -1,
            "neo4j_node_id": node_id,
        }
        if cname:
            payload["cluster_name"] = cname
        if cdesc:
            payload["cluster_description"] = cdesc
        if reason:
            payload["anomaly_reason"] = reason

        pid = point["point_id"]
        if isinstance(pid, str) and pid.isdigit():
            pid = int(pid)
        try:
            await qdrant.set_payload(
                collection_name=settings.qdrant_collection_claims,
                payload=payload,
                points=[pid],
            )
        except Exception as exc:
            log.warning("qdrant set_payload failed point=%s: %s", point["point_id"], exc)

    for doc_id, bucket in per_document.items():
        cid_set = bucket.pop("_cluster_ids", set())
        bucket["clusters"] = len(cid_set)

    valid_clusters = {c for c in cluster_ids if c >= 0}
    named_clusters = [
        {
            "id": cid,
            "name": cluster_names[cid],
            "description": cluster_descriptions.get(cid, ""),
            "members": len(members_by_cluster.get(cid, [])),
        }
        for cid in sorted(valid_clusters)
    ]
    all_noise = len(valid_clusters) == 0 and clustered > 0
    return {
        "clustered": clustered,
        "anomalies": anomalies,
        "points": len(points),
        "clusters": len(valid_clusters),
        "global": True,
        "cluster_names": {str(k): v for k, v in cluster_names.items()},
        "cluster_descriptions": {str(k): v for k, v in cluster_descriptions.items()},
        "named_clusters": named_clusters,
        "per_document": per_document,
        "min_cluster_size": mcs,
        "min_samples": used_min_samples if used_min_samples is not None else mcs,
        "all_noise": all_noise,
        "noise_hint": (
            "HDBSCAN пометил все точки как noise: эмбеддинги слишком разрознены для текущих "
            f"min_cluster_size={mcs}. Добавьте похожие документы или уменьшите HDBSCAN_MIN_CLUSTER_SIZE в .env."
            if all_noise
            else None
        ),
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
                "cluster_name": props.get("cluster_name"),
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


async def get_l4_clustering_context(*, document_id: str | None = None) -> dict[str, Any]:
    """Статистика корпуса и параметры HDBSCAN для UI (пустое состояние карты)."""
    from mkg_core.embeddings import count_indexed_points

    settings = get_settings()
    repo = get_repo()
    items, _ = repo.list(1, 500)
    doc_total = len(items)
    docs_with_graph = sum(1 for r in items if (r.get("graph_nodes") or 0) > 0)
    counts = await count_indexed_points(document_id=document_id)
    l4_points = int(counts.get(settings.qdrant_collection_claims) or 0)
    l3_points = int(counts.get(settings.qdrant_collection_chunks) or 0)
    per_doc_l4 = [int(r.get("l4_points") or 0) for r in items if (r.get("l4_points") or 0) > 0]
    avg_l4_per_doc = round(sum(per_doc_l4) / len(per_doc_l4), 1) if per_doc_l4 else 0.0

    qdrant = QdrantClientSingleton.instance().client
    filt_must = [FieldCondition(key="layer", match=MatchValue(value="L4"))]
    if document_id:
        filt_must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
    offset = None
    labeled = 0
    anomalies = 0
    cluster_ids: set[int] = set()
    has_labels = False
    while True:
        records, offset = await qdrant.scroll(
            collection_name=settings.qdrant_collection_claims,
            scroll_filter=Filter(must=filt_must),
            limit=128,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for rec in records:
            payload = dict(rec.payload or {})
            cid = payload.get("cluster_id")
            if cid is not None:
                has_labels = True
                labeled += 1
                cid_int = int(cid)
                if cid_int >= 0:
                    cluster_ids.add(cid_int)
                else:
                    anomalies += 1
        if offset is None or not records:
            break

    ms = settings.hdbscan_min_samples
    mcs = settings.hdbscan_min_cluster_size
    return {
        "document_id": document_id,
        "doc_count": doc_total,
        "docs_with_graph": docs_with_graph,
        "l3_points": l3_points,
        "l4_points": l4_points,
        "avg_l4_per_doc": avg_l4_per_doc,
        "min_cluster_size": mcs,
        "min_samples": ms if ms is not None else mcs,
        "has_cluster_labels": has_labels,
        "cluster_count": len(cluster_ids),
        "anomaly_count": anomalies,
        "clustering_ran": has_labels,
    }


def _node_text_from_graph(node: dict[str, Any]) -> str:
    return _node_text(node)


def _collect_graphs(document_id: str | None) -> list[tuple[str, dict[str, Any]]]:
    repo = get_repo()
    if document_id:
        g = repo.read_graph(document_id)
        return [(document_id, g)] if g else []
    items, _ = repo.list(1, 500)
    out: list[tuple[str, dict[str, Any]]] = []
    for rec in items:
        g = repo.read_graph(rec["id"])
        if g and g.get("nodes"):
            out.append((rec["id"], g))
    return out


def _l4_cluster_map_from_graphs(graphs: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """node_id → {cluster_id, cluster_name, cluster_description, document_id, label, text}."""
    out: dict[str, dict[str, Any]] = {}
    for doc_id, graph in graphs:
        for node in _l4_nodes_in_graph(graph):
            nid = str(node.get("id") or "")
            if not nid:
                continue
            props = dict(node.get("props") or {})
            out[nid] = {
                "node_id": nid,
                "document_id": doc_id,
                "label": str(node.get("label") or ""),
                "text": str(
                    props.get("text_ru") or props.get("title_ru") or props.get("quote") or _node_text(node)
                )[:400],
                "cluster_id": props.get("cluster_id"),
                "cluster_name": props.get("cluster_name"),
                "cluster_description": props.get("cluster_description"),
                "anomaly_score": props.get("anomaly_score"),
                "anomaly_reason": props.get("anomaly_reason"),
                "is_anomaly": props.get("is_anomaly"),
            }
    return out


def _edges_for_cluster(
    cluster_id: int,
    member_ids: set[str],
    l4_map: dict[str, dict[str, Any]],
    graphs: list[tuple[str, dict[str, Any]]],
    *,
    limit: int = 40,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    internal: list[dict[str, Any]] = []
    cross: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for doc_id, graph in graphs:
        for rel in graph.get("relationships") or []:
            fr = str(rel.get("from") or "")
            to = str(rel.get("to") or "")
            rtype = str(rel.get("type") or "")
            if fr not in member_ids and to not in member_ids:
                continue
            key = (doc_id, fr, to, rtype)
            if key in seen:
                continue
            seen.add(key)
            edge = {
                "document_id": doc_id,
                "from_node": fr,
                "to_node": to,
                "type": rtype,
                "from_label": l4_map.get(fr, {}).get("label"),
                "to_label": l4_map.get(to, {}).get("label"),
            }
            if fr in member_ids and to in member_ids:
                if len(internal) < limit:
                    internal.append(edge)
            elif fr in member_ids or to in member_ids:
                other = to if fr in member_ids else fr
                other_info = l4_map.get(other, {})
                other_cid = other_info.get("cluster_id")
                if other_cid is not None and int(other_cid) >= 0 and int(other_cid) != cluster_id:
                    edge["other_cluster_id"] = int(other_cid)
                    edge["other_cluster_name"] = other_info.get("cluster_name")
                    if len(cross) < limit:
                        cross.append(edge)
    return internal, cross


async def get_cluster_detail(cluster_id: int, *, document_id: str | None = None) -> dict[str, Any]:
    """Детали кластера: описание, участники, связи Neo4j."""
    if cluster_id < 0:
        raise ValueError("cluster_id must be >= 0")

    qdrant = QdrantClientSingleton.instance().client
    settings = get_settings()
    members: list[dict[str, Any]] = []
    cluster_name = None
    cluster_description = None

    filt_must = [FieldCondition(key="layer", match=MatchValue(value="L4"))]
    if document_id:
        filt_must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
    offset = None
    while True:
        records, offset = await qdrant.scroll(
            collection_name=settings.qdrant_collection_claims,
            scroll_filter=Filter(must=filt_must),
            limit=128,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for rec in records:
            payload = dict(rec.payload or {})
            cid = payload.get("cluster_id")
            if cid is None or int(cid) != cluster_id:
                continue
            nid = str(payload.get("neo4j_node_id") or payload.get("node_id") or "")
            if cluster_name is None and payload.get("cluster_name"):
                cluster_name = str(payload["cluster_name"])
            if cluster_description is None and payload.get("cluster_description"):
                cluster_description = str(payload["cluster_description"])
            members.append(
                {
                    "node_id": nid,
                    "document_id": str(payload.get("document_id") or ""),
                    "label": str(payload.get("label") or ""),
                    "text": str(payload.get("text") or "")[:300],
                }
            )
        if offset is None or not records:
            break

    member_ids = {m["node_id"] for m in members if m.get("node_id")}
    graphs = _collect_graphs(document_id)
    l4_map = _l4_cluster_map_from_graphs(graphs)
    if not cluster_name:
        for nid in member_ids:
            info = l4_map.get(nid, {})
            if info.get("cluster_name"):
                cluster_name = info["cluster_name"]
                cluster_description = cluster_description or info.get("cluster_description")
                break
    cluster_name = cluster_name or f"Кластер {cluster_id}"
    if not cluster_description:
        texts = [m.get("text") or "" for m in members if m.get("text")]
        cluster_description = _heuristic_cluster_description(texts, cluster_name)

    internal, cross = _edges_for_cluster(cluster_id, member_ids, l4_map, graphs)
    ctx = await get_l4_clustering_context(document_id=document_id)

    return {
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "cluster_description": cluster_description,
        "point_count": len(members),
        "members": members[:50],
        "internal_edges": internal,
        "cross_cluster_edges": cross,
        "clustering_context": ctx,
    }


def _nearest_cluster(
    vector: list[float],
    points: list[dict[str, Any]],
    labels: list[int],
    cluster_names: dict[int, str],
) -> dict[str, Any] | None:
    import numpy as np

    centroids: dict[int, list[np.ndarray]] = {}
    for p, lbl in zip(points, labels):
        if lbl < 0:
            continue
        centroids.setdefault(lbl, []).append(np.asarray(p["vector"], dtype=np.float64))
    if not centroids:
        return None
    v = np.asarray(vector, dtype=np.float64)
    best_id = None
    best_dist = float("inf")
    for cid, vecs in centroids.items():
        center = np.mean(vecs, axis=0)
        dist = float(np.linalg.norm(v - center))
        if dist < best_dist:
            best_dist = dist
            best_id = cid
    if best_id is None:
        return None
    return {
        "cluster_id": best_id,
        "cluster_name": cluster_names.get(best_id, f"Кластер {best_id}"),
        "distance": round(best_dist, 4),
    }


async def get_l4_point_detail(node_id: str, *, document_id: str | None = None) -> dict[str, Any]:
    """Детали L4-точки: текст, причина аномалии, ближайший кластер."""
    node_id = (node_id or "").strip()
    if not node_id:
        raise ValueError("node_id required")

    settings = get_settings()
    qdrant = QdrantClientSingleton.instance().client
    filt_must = [FieldCondition(key="layer", match=MatchValue(value="L4"))]
    if document_id:
        filt_must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))

    target: dict[str, Any] | None = None
    offset = None
    while True:
        records, offset = await qdrant.scroll(
            collection_name=settings.qdrant_collection_claims,
            scroll_filter=Filter(must=filt_must),
            limit=128,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        for rec in records:
            payload = dict(rec.payload or {})
            nid = str(payload.get("neo4j_node_id") or payload.get("node_id") or "")
            if nid != node_id:
                continue
            vector = rec.vector
            if isinstance(vector, dict):
                vector = next(iter(vector.values()), None)
            target = {
                "node_id": nid,
                "point_id": str(rec.id),
                "document_id": str(payload.get("document_id") or ""),
                "label": str(payload.get("label") or ""),
                "text": str(payload.get("text") or "")[:500],
                "cluster_id": payload.get("cluster_id"),
                "cluster_name": payload.get("cluster_name"),
                "is_anomaly": payload.get("is_anomaly"),
                "anomaly_score": payload.get("anomaly_score"),
                "anomaly_reason": payload.get("anomaly_reason"),
                "vector": list(vector) if vector else None,
            }
            break
        if target or offset is None or not records:
            break

    if not target:
        graphs = _collect_graphs(document_id)
        l4_map = _l4_cluster_map_from_graphs(graphs)
        info = l4_map.get(node_id)
        if not info:
            raise ValueError(f"L4 point not found: {node_id}")
        target = {**info, "point_id": None, "vector": None}

    cid = target.get("cluster_id")
    is_anomaly = target.get("is_anomaly") is True or (cid is not None and int(cid) < 0)
    reason = str(target.get("anomaly_reason") or "")
    if is_anomaly and not reason:
        reason = _anomaly_reason({"is_anomaly": True}, int(cid) if cid is not None else -1)
        if reason == "hdbscan_noise":
            reason = (
                "HDBSCAN пометил точку как noise (cluster_id=-1): семантически не похожа "
                "ни на одну плотную группу L4-фактов в корпусе."
            )

    nearest = None
    if is_anomaly and target.get("vector"):
        all_points = await fetch_l4_vectors(document_id=document_id, limit=10000)
        if all_points:
            vectors = np.array([p["vector"] for p in all_points], dtype=np.float64)
            mcs = settings.hdbscan_min_cluster_size
            ms = settings.hdbscan_min_samples
            labels, _ = cluster_vectors(vectors, min_cluster_size=mcs, min_samples=ms)
            if not {c for c in labels if c >= 0} and mcs <= 2:
                labels, _ = cluster_vectors(vectors, min_cluster_size=mcs, min_samples=1)
            members_by_cluster: dict[int, list[str]] = {}
            for p, lbl in zip(all_points, labels):
                if lbl >= 0:
                    members_by_cluster.setdefault(lbl, []).append(p.get("text") or "")
            names = {cid: _heuristic_cluster_name(texts, cid) for cid, texts in members_by_cluster.items()}
            nearest = _nearest_cluster(target["vector"], all_points, labels, names)

    graphs = _collect_graphs(document_id)
    l4_map = _l4_cluster_map_from_graphs(graphs)
    member_ids = {node_id}
    internal, cross = _edges_for_cluster(
        int(cid) if cid is not None and int(cid) >= 0 else -999,
        member_ids,
        l4_map,
        graphs,
        limit=20,
    )
    edges = internal + cross

    return {
        **target,
        "is_anomaly": is_anomaly,
        "anomaly_reason": reason,
        "nearest_cluster": nearest,
        "edges": edges[:25],
        "clustering_context": await get_l4_clustering_context(document_id=document_id),
    }


async def apply_global_l4_cluster(
    trigger_document_id: str | None = None,
    *,
    force: bool = False,
    min_cluster_size: int | None = None,
) -> dict[str, Any]:
    """Глобальная HDBSCAN-кластеризация L4 с debounce через Redis."""
    from mkg_core.meta_db import update_document_status

    if not force and not await _try_acquire_cluster_lock():
        log.info("l4 global cluster debounced trigger_doc=%s", trigger_document_id)
        return {
            "debounced": True,
            "global": True,
            "document_id": trigger_document_id,
            "message": f"Кластеризация отложена (debounce {_CLUSTER_DEBOUNCE_SECS}s)",
        }

    repo = get_repo()
    if trigger_document_id:
        rec = repo.get(trigger_document_id) or {}
        if rec.get("processing_mode") == "answers_only":
            return {"skipped": True, "reason": "answers_only", "document_id": trigger_document_id}
        status = rec.get("status") or "loaded"
        repo.set_status(trigger_document_id, status, step="l4_cluster", l4_error=None)
        try:
            await update_document_status(trigger_document_id, status, step="l4_cluster", l4_error=None)
        except Exception as exc:
            log.warning("postgres update failed l4_cluster start doc_id=%s: %s", trigger_document_id, exc)

    try:
        stats = await run_l4_clustering(min_cluster_size=min_cluster_size)
        _update_all_documents_l4_status(stats)
        try:
            items, _ = repo.list(1, 500)
            for rec in items:
                doc_id = rec["id"]
                per_doc = (stats.get("per_document") or {}).get(doc_id)
                if not per_doc and not stats.get("clustered"):
                    continue
                extra = {
                    "l4_clusters": int(stats.get("clusters") or 0),
                    "l4_anomalies": per_doc.get("anomalies", 0) if per_doc else 0,
                    "l4_clustered": per_doc.get("clustered", 0) if per_doc else 0,
                    "l4_points": per_doc.get("points", 0) if per_doc else 0,
                    "step": "l4_done",
                    "l4_error": None,
                }
                status = rec.get("status") or "loaded"
                repo.set_status(doc_id, status, **extra)
                try:
                    await update_document_status(doc_id, status, **extra)
                except Exception:
                    pass
        except Exception as exc:
            log.warning("postgres bulk l4_done update failed: %s", exc)

        log.info(
            "l4 global cluster done clusters=%s anomalies=%s points=%s trigger=%s",
            stats.get("clusters"),
            stats.get("anomalies"),
            stats.get("points"),
            trigger_document_id,
        )
        return {**stats, "document_id": trigger_document_id, "step": "l4_done"}
    except Exception as exc:
        log.warning("l4 global cluster failed: %s", exc)
        if trigger_document_id:
            rec = repo.get(trigger_document_id) or {}
            status = rec.get("status") or "loaded"
            repo.set_status(trigger_document_id, status, step="l4_failed", l4_error=str(exc))
            try:
                await update_document_status(trigger_document_id, status, step="l4_failed", l4_error=str(exc))
            except Exception:
                pass
        return {"document_id": trigger_document_id, "error": str(exc), "step": "l4_failed", "global": True}


async def cluster_document_l4(
    document_id: str,
    graph: dict[str, Any],
    *,
    min_cluster_size: int | None = None,
    index_if_missing: bool = True,
) -> dict[str, Any]:
    """Индексирует L4 документа при необходимости, затем глобальная кластеризация."""
    from mkg_core.embeddings import count_indexed_points, index_document_graph

    l4_nodes = _l4_nodes_in_graph(graph)
    if index_if_missing and l4_nodes:
        counts = await count_indexed_points(document_id=document_id)
        if not counts.get(get_settings().qdrant_collection_claims):
            await index_document_graph(document_id, graph)

    stats = await apply_global_l4_cluster(document_id, force=True)
    fresh = get_repo().read_graph(document_id) or graph
    graph.clear()
    graph.update(fresh)

    structural = sum(
        1 for n in l4_nodes
        if not (n.get("props") or {}).get("text_ru") and not (n.get("props") or {}).get("title_ru")
    )
    hdbscan_anomalies = int(stats.get("anomalies") or 0)
    per_doc = (stats.get("per_document") or {}).get(document_id, {})
    return {
        "document_id": document_id,
        "l4_nodes": len(l4_nodes),
        "vectors_found": int(stats.get("points") or 0),
        "clustered": int(per_doc.get("clustered") or stats.get("clustered") or 0),
        "hdbscan_anomalies": hdbscan_anomalies,
        "structural_anomalies": structural,
        "total_anomalies": hdbscan_anomalies + structural,
        "global": True,
        "cluster_names": stats.get("cluster_names") or {},
        "named_clusters": stats.get("named_clusters") or [],
    }


async def apply_document_l4_cluster(document_id: str) -> dict[str, Any]:
    """После Qdrant: глобальная HDBSCAN L4 (debounced)."""
    return await apply_global_l4_cluster(document_id)
