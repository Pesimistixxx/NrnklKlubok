"""Кластеризация фактов и поиск аномалий.

Алгоритм: HDBSCAN по векторам утверждений/измерений из Qdrant.
- cluster_id  — метка кластера («факты об одном и том же»),
- anomaly_score — GLOSH outlier score HDBSCAN (чем выше, тем аномальнее).
Метки пишутся обратно в Neo4j как свойства узлов Claim/Measurement.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import hdbscan
except Exception:  # pragma: no cover
    hdbscan = None


@dataclass
class ClusterResult:
    labels: list[int]
    anomaly_scores: list[float]


def cluster_and_score(
    vectors: np.ndarray,
    *,
    min_cluster_size: int = 3,
    min_samples: int | None = None,
    metric: str = "euclidean",
) -> ClusterResult:
    """Кластеризация HDBSCAN + оценка аномальности (GLOSH)."""
    if hdbscan is None:
        raise RuntimeError("hdbscan не установлен: pip install hdbscan")
    if len(vectors) == 0:
        return ClusterResult(labels=[], anomaly_scores=[])

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        prediction_data=True,
    )
    labels = clusterer.fit_predict(vectors)          # -1 = шум/выброс
    outlier = getattr(clusterer, "outlier_scores_", np.zeros(len(vectors)))
    outlier = np.nan_to_num(outlier, nan=0.0)
    return ClusterResult(
        labels=[int(x) for x in labels],
        anomaly_scores=[float(x) for x in outlier],
    )


async def run() -> dict[str, int]:
    """Полный проход: вектора из Qdrant → кластеры/аномалии → метки в Neo4j.

    Этап 3: здесь читаем точки коллекции mkg_claims из Qdrant, кластеризуем,
    и обновляем Neo4j (Claim.cluster_id, Claim.anomaly_score) по payload.neo4j_id.
    """
    # TODO(этап 3): выгрузка векторов из Qdrant + запись меток в Neo4j.
    return {"clustered": 0, "anomalies": 0}
