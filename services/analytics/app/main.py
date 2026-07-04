"""MKG Analytics — достоверность, противоречия, кластеры/аномалии.

Запускается по событию загрузки (через очередь) и по расписанию. На этапе 3 подключается
к Neo4j/Qdrant. Здесь — точка входа и связка модулей.
Документация: Docs/02_architecture.md и Docs/13_roadmap.md.
"""
from __future__ import annotations

import asyncio

from app.clustering import run as run_clustering
from app.confidence import compute, corroboration, load_runtime_config, recency, source_reliability


async def recompute_all() -> dict:
    """Этап 3: пересчёт доверия по всему графу + кластеры/аномалии."""
    await load_runtime_config()
    clusters = await run_clustering()
    return {"clusters": clusters}


def _demo() -> None:
    """Демонстрация расчёта композитного доверия (без БД)."""
    breakdown = compute(
        {
            "source_reliability": source_reliability("статья", verified=True),
            "extraction_confidence": 0.8,
            "corroboration": corroboration(2),
            "consistency": 1.0,
            "recency": recency(years_old=4),
        }
    )
    print("confidence:", breakdown.confidence)
    print("components:", breakdown.components)


if __name__ == "__main__":
    _demo()
    asyncio.run(recompute_all())
