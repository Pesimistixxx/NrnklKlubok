"""Кластеризация фактов и поиск аномалий — делегирует в mkg_core.l4_clustering."""
from __future__ import annotations

from mkg_core.l4_clustering import run_l4_clustering


async def run() -> dict[str, int]:
    """Полный проход: вектора L4 из Qdrant → HDBSCAN → метки в Neo4j/JSON."""
    result = await run_l4_clustering()
    return {
        "clustered": int(result.get("clustered") or 0),
        "anomalies": int(result.get("anomalies") or 0),
        "clusters": int(result.get("clusters") or 0),
    }
