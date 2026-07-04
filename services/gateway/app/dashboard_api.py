"""Manager dashboard: coverage stats and risk zones (hackathon MVP)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.l4_clustering import list_anomalies_from_graph

from app.storage import get_repo

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_DOMAIN_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("hydromet", "Гидрометаллургия", ("гидромет", "leach", "выщел", "осадк", "сток", "металл", "cu", "ni", "zn")),
    ("ecology", "Экология", ("экolog", "окружа", "природ", "environment", "эко", "выброс", "загрязн")),
    ("waste", "Отходы и хвосты", ("отход", "хвост", "tailings", "шлам", "waste", "склад")),
]


def _domain_from_title(title: str) -> str | None:
    blob = (title or "").lower()
    for domain_id, _label, keys in _DOMAIN_RULES:
        if any(k in blob for k in keys):
            return domain_id
    return None


def _count_nodes(graph: dict[str, Any], label: str) -> int:
    return sum(1 for n in graph.get("nodes") or [] if str(n.get("label") or "") == label)


def _sparse_l4_clusters(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Clusters with only 1–2 L4 nodes — risk of thin evidence."""
    by_cluster: dict[int, list[str]] = {}
    for node in graph.get("nodes") or []:
        if str(node.get("label") or "") not in ("Measurement", "ExperimentRun", "TechStage", "Effect", "Claim"):
            continue
        props = node.get("props") if isinstance(node.get("props"), dict) else {}
        cid = props.get("cluster_id")
        if cid is None:
            continue
        try:
            cluster_int = int(cid)
        except (TypeError, ValueError):
            continue
        if cluster_int < 0:
            continue
        by_cluster.setdefault(cluster_int, []).append(str(node.get("id") or ""))
    sparse: list[dict[str, Any]] = []
    for cid, nodes in by_cluster.items():
        if len(nodes) <= 2:
            sparse.append({"cluster_id": cid, "node_count": len(nodes), "sample_nodes": nodes[:3]})
    return sparse


@router.get("/stats")
async def dashboard_stats() -> dict[str, Any]:
    repo = get_repo()
    items, total = repo.list(page=1, page_size=500)
    doc_count = total or len(items)

    domain_counts: dict[str, dict[str, Any]] = {
        d[0]: {"id": d[0], "label": d[1], "doc_count": 0} for d in _DOMAIN_RULES
    }
    domain_counts["other"] = {"id": "other", "label": "Прочее", "doc_count": 0}

    l4_anomalies = 0
    contradiction_nodes = 0
    risk_zones: list[dict[str, Any]] = []

    for rec in items:
        title = str(rec.get("file_name") or rec.get("id") or "")
        dom = _domain_from_title(title) or "other"
        domain_counts[dom]["doc_count"] = int(domain_counts[dom]["doc_count"]) + 1

        graph_raw = repo.read_graph(rec["id"])
        if not graph_raw or not graph_raw.get("nodes"):
            continue
        graph = dedupe_graph_payload(
            GraphPayload(
                nodes=list(graph_raw.get("nodes") or []),
                relationships=list(graph_raw.get("relationships") or []),
            )
        ).as_dict()
        doc_id = rec["id"]

        anomalies = list_anomalies_from_graph(graph, document_id=doc_id, limit=500)
        l4_anomalies += len(anomalies)
        for a in anomalies[:3]:
            risk_zones.append(
                {
                    "type": "l4_anomaly",
                    "severity": "medium",
                    "document_id": doc_id,
                    "title": a.get("label") or a.get("node_id") or "L4-аномалия",
                    "detail": (a.get("text") or "")[:160],
                    "node_id": a.get("node_id"),
                }
            )

        for node in graph.get("nodes") or []:
            if str(node.get("label") or "") != "Contradiction":
                continue
            contradiction_nodes += 1
            props = node.get("props") if isinstance(node.get("props"), dict) else {}
            risk_zones.append(
                {
                    "type": "contradiction",
                    "severity": "high",
                    "document_id": doc_id,
                    "title": str(props.get("title") or props.get("text") or node.get("id") or "Противоречие")[:120],
                    "detail": str(props.get("description") or props.get("text") or "")[:160],
                    "node_id": str(node.get("id") or ""),
                }
            )

        for sparse in _sparse_l4_clusters(graph):
            risk_zones.append(
                {
                    "type": "sparse_l4",
                    "severity": "low",
                    "document_id": doc_id,
                    "title": f"Разреженный L4-кластер #{sparse['cluster_id']}",
                    "detail": f"{sparse['node_count']} факт(ов) — мало источников для выводов",
                    "cluster_id": sparse["cluster_id"],
                }
            )

    # Dedupe risk list, cap size
    seen_risk: set[str] = set()
    unique_risks: list[dict[str, Any]] = []
    for rz in sorted(risk_zones, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(str(x.get("severity")), 3)):
        key = f"{rz.get('type')}:{rz.get('document_id')}:{rz.get('node_id') or rz.get('cluster_id')}"
        if key in seen_risk:
            continue
        seen_risk.add(key)
        unique_risks.append(rz)
        if len(unique_risks) >= 24:
            break

    domains = [v for v in domain_counts.values() if v["doc_count"] > 0]
    domains.sort(key=lambda d: -int(d["doc_count"]))

    return {
        "doc_count": doc_count,
        "l4_anomalies_count": l4_anomalies,
        "contradiction_nodes_count": contradiction_nodes,
        "domains": domains,
        "risk_zones": unique_risks,
    }
