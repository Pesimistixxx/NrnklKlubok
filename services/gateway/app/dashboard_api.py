"""Manager dashboard: coverage stats and risk zones (hackathon MVP)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from mkg_core.comparison import merge_repo_comparison, rows_to_csv
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.l4_clustering import list_anomalies_from_graph

from app.collab_db import collab_activity_stats
from app.storage import get_repo

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MKG_APP_VERSION = "0.9.0"

_DOMAIN_RULES: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("hydromet", "Гидрометаллургия", "Hydrometallurgy", ("гидромет", "leach", "выщел", "осадк", "сток", "металл", "cu", "ni", "zn")),
    ("ecology", "Экология", "Ecology", ("экolog", "окружа", "природ", "environment", "эко", "выброс", "загрязн")),
    ("waste", "Отходы и хвосты", "Waste & tailings", ("отход", "хвост", "tailings", "шлам", "waste", "склад")),
]

_L4_LABELS = frozenset(
    {"Measurement", "ExperimentRun", "TechStage", "Effect", "Claim", "Deviation", "TrendVector"}
)


def _domain_from_title(title: str) -> str | None:
    blob = (title or "").lower()
    for domain_id, _label, _label_en, keys in _DOMAIN_RULES:
        if any(k in blob for k in keys):
            return domain_id
    return None


def _count_nodes(graph: dict[str, Any], label: str) -> int:
    return sum(1 for n in graph.get("nodes") or [] if str(n.get("label") or "") == label)


def _count_l4_nodes(graph: dict[str, Any]) -> int:
    return sum(1 for n in graph.get("nodes") or [] if str(n.get("label") or "") in _L4_LABELS)


def _node_display_name(node: dict[str, Any]) -> str:
    props = node.get("props") if isinstance(node.get("props"), dict) else {}
    for key in ("name_ru", "name_en", "name", "title", "text"):
        val = props.get(key)
        if val:
            return str(val)[:120]
    return str(node.get("id") or "—")[:120]


def _sparse_l4_clusters(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Clusters with only 1–2 L4 nodes — risk of thin evidence."""
    by_cluster: dict[int, list[str]] = {}
    for node in graph.get("nodes") or []:
        if str(node.get("label") or "") not in _L4_LABELS:
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


def _extract_tech_comparison(items: list[dict[str, Any]], repo: Any, *, limit: int = 10) -> list[dict[str, Any]]:
    """Process/Material/TechnologySolution с параметрами из Measurement и L6-индикаторов."""
    doc_ids = [rec["id"] for rec in items]
    rows, _meta = merge_repo_comparison(repo, document_ids=doc_ids, limit=limit)
    return rows


def _recent_uploads(items: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    dated: list[tuple[str, dict[str, Any]]] = []
    for rec in items:
        raw = rec.get("upload_date") or rec.get("created_at") or ""
        dated.append((str(raw), rec))
    dated.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for _dt, rec in dated[:limit]:
        out.append(
            {
                "id": rec.get("id"),
                "file_name": rec.get("file_name"),
                "upload_date": _dt or None,
                "status": rec.get("status"),
            }
        )
    return out


@router.get("/stats")
async def dashboard_stats() -> dict[str, Any]:
    repo = get_repo()
    items, total = repo.list(page=1, page_size=500)
    doc_count = total or len(items)

    domain_counts: dict[str, dict[str, Any]] = {
        d[0]: {"id": d[0], "label": d[1], "label_en": d[2], "doc_count": 0, "node_count": 0}
        for d in _DOMAIN_RULES
    }
    domain_counts["other"] = {"id": "other", "label": "Прочее", "label_en": "Other", "doc_count": 0, "node_count": 0}

    l4_anomalies = 0
    contradiction_nodes = 0
    total_l4_nodes = 0
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
        l4_in_doc = _count_l4_nodes(graph)
        total_l4_nodes += l4_in_doc
        if dom in domain_counts:
            domain_counts[dom]["node_count"] = int(domain_counts[dom]["node_count"]) + l4_in_doc

        anomalies = list_anomalies_from_graph(graph, document_id=doc_id, limit=500)
        l4_anomalies += len(anomalies)
        for a in anomalies[:3]:
            topic = a.get("label") or a.get("node_id") or "L4-аномалия"
            risk_zones.append(
                {
                    "type": "l4_anomaly",
                    "severity": "medium",
                    "document_id": doc_id,
                    "topic": topic,
                    "title": topic,
                    "detail": (a.get("text") or "")[:160],
                    "node_id": a.get("node_id"),
                    "source_count": 1,
                    "contradiction_flag": False,
                }
            )

        for node in graph.get("nodes") or []:
            if str(node.get("label") or "") != "Contradiction":
                continue
            contradiction_nodes += 1
            props = node.get("props") if isinstance(node.get("props"), dict) else {}
            topic = str(props.get("title") or props.get("text") or node.get("id") or "Противоречие")[:120]
            risk_zones.append(
                {
                    "type": "contradiction",
                    "severity": "high",
                    "document_id": doc_id,
                    "topic": topic,
                    "title": topic,
                    "detail": str(props.get("description") or props.get("text") or "")[:160],
                    "node_id": str(node.get("id") or ""),
                    "source_count": 1,
                    "contradiction_flag": True,
                }
            )

        for sparse in _sparse_l4_clusters(graph):
            topic = f"Разреженный L4-кластер #{sparse['cluster_id']}"
            risk_zones.append(
                {
                    "type": "sparse_l4",
                    "severity": "low",
                    "document_id": doc_id,
                    "topic": topic,
                    "title": topic,
                    "detail": f"{sparse['node_count']} факт(ов) — мало источников для выводов",
                    "cluster_id": sparse["cluster_id"],
                    "source_count": sparse["node_count"],
                    "contradiction_flag": False,
                }
            )

    # Domain coverage with %
    domain_coverage: dict[str, dict[str, Any]] = {}
    for d in _DOMAIN_RULES:
        dom_id = d[0]
        entry = domain_counts[dom_id]
        node_n = int(entry["node_count"])
        doc_n = int(entry["doc_count"])
        pct = round(100.0 * node_n / total_l4_nodes, 1) if total_l4_nodes > 0 else 0.0
        if doc_count > 0 and node_n == 0:
            pct = round(100.0 * doc_n / doc_count, 1)
        domain_coverage[dom_id] = {
            "id": dom_id,
            "label": entry["label"],
            "label_en": entry["label_en"],
            "doc_count": doc_n,
            "node_count": node_n,
            "coverage_pct": pct,
        }

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

    team_activity: dict[str, Any] = {
        "doc_count": doc_count,
        "recent_uploads": _recent_uploads(items),
        "thread_count": 0,
        "message_count": 0,
        "queries_7d": 0,
    }
    try:
        collab = await collab_activity_stats()
        team_activity.update(collab)
    except Exception:
        pass

    tech_comparison = _extract_tech_comparison(items, repo)

    return {
        "app_version": MKG_APP_VERSION,
        "build_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "doc_count": doc_count,
        "l4_anomalies_count": l4_anomalies,
        "contradiction_nodes_count": contradiction_nodes,
        "total_l4_nodes": total_l4_nodes,
        "domain_coverage": domain_coverage,
        "domains": domains,
        "team_activity": team_activity,
        "tech_comparison": tech_comparison,
        "risk_zones": unique_risks,
    }


@router.get("/export/stats.json")
async def export_stats_json() -> dict[str, Any]:
    """Full dashboard payload for offline analysis."""
    return await dashboard_stats()


@router.get("/export/stats.csv")
async def export_stats_csv() -> dict[str, str]:
    """CSV summary of headline metrics and domains."""
    data = await dashboard_stats()
    lines = [
        "metric,value",
        f"app_version,{data.get('app_version', '')}",
        f"doc_count,{data.get('doc_count', 0)}",
        f"l4_anomalies_count,{data.get('l4_anomalies_count', 0)}",
        f"contradiction_nodes_count,{data.get('contradiction_nodes_count', 0)}",
        f"total_l4_nodes,{data.get('total_l4_nodes', 0)}",
        "",
        "domain_id,domain_label,doc_count,node_count,coverage_pct",
    ]
    for dom_id, dom in (data.get("domain_coverage") or {}).items():
        label = str(dom.get("label") or "").replace('"', '""')
        lines.append(
            f'{dom.get("id")},"{label}",{dom.get("doc_count", 0)},{dom.get("node_count", 0)},{dom.get("coverage_pct", 0)}'
        )
    return {"filename": "mkg-dashboard.csv", "content": "\n".join(lines)}


@router.get("/export/compare.csv")
async def export_compare_csv() -> dict[str, str]:
    """CSV export of technology comparison table."""
    repo = get_repo()
    items, _total = repo.list(page=1, page_size=500)
    rows, _meta = merge_repo_comparison(repo, document_ids=[rec["id"] for rec in items], limit=30)
    return {"filename": "mkg-tech-comparison.csv", "content": rows_to_csv(rows)}


@router.get("/export/risks.csv")
async def export_risks_csv() -> dict[str, str]:
    """CSV export of risk zones."""
    data = await dashboard_stats()
    header = "type,severity,topic,source_count,contradiction_flag,document_id,detail,node_id,cluster_id"
    rows = [header]
    for rz in data.get("risk_zones") or []:
        cells = [
            str(rz.get("type") or ""),
            str(rz.get("severity") or ""),
            str(rz.get("topic") or rz.get("title") or "").replace('"', '""'),
            str(rz.get("source_count") or ""),
            "yes" if rz.get("contradiction_flag") else "no",
            str(rz.get("document_id") or ""),
            str(rz.get("detail") or "").replace('"', '""'),
            str(rz.get("node_id") or ""),
            str(rz.get("cluster_id") or ""),
        ]
        rows.append(",".join(
            f'"{c}"' if i in (2, 6) else c for i, c in enumerate(cells)
        ))
    return {"filename": "mkg-risks.csv", "content": "\n".join(rows)}
