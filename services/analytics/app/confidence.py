"""Композитная модель достоверности.

Реализация формулы: confidence = Σ wᵢ·componentᵢ. Объяснимо и пересчитываемо.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass

import asyncpg

from mkg_core import get_settings

FORMULA_VERSION = "v1"

FALLBACK_WEIGHTS = {
    "source_reliability": 0.30,
    "extraction_confidence": 0.25,
    "corroboration": 0.20,
    "consistency": 0.15,
    "recency": 0.10,
}

FALLBACK_SOURCE_RELIABILITY = {
    "статья": 0.90,
    "патент": 0.80,
    "диссертация": 0.80,
    "книга": 0.75,
    "отчёт": 0.70,
    "отчёт_черновой": 0.50,
    "препринт": 0.40,
}


@dataclass
class RuntimeConfidenceConfig:
    weights: dict[str, float]
    source_reliability: dict[str, float]


@dataclass
class ConfidenceBreakdown:
    confidence: float
    components: dict[str, float]
    weights: dict[str, float]
    formula_version: str = FORMULA_VERSION


_CONFIG_CACHE = RuntimeConfidenceConfig(
    weights=dict(FALLBACK_WEIGHTS),
    source_reliability=dict(FALLBACK_SOURCE_RELIABILITY),
)
_CONFIG_READY = False
_CONFIG_LOCK: asyncio.Lock | None = None
_POOL: asyncpg.Pool | None = None


def _db_dsn() -> str:
    dsn = get_settings().database_url
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return dsn


async def _pool() -> asyncpg.Pool:
    global _POOL
    if _POOL is None:
        _POOL = await asyncpg.create_pool(_db_dsn(), min_size=1, max_size=3)
    return _POOL


def _config_lock() -> asyncio.Lock:
    global _CONFIG_LOCK
    if _CONFIG_LOCK is None:
        _CONFIG_LOCK = asyncio.Lock()
    return _CONFIG_LOCK


async def _ensure_config_tables(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS confidence_weights (
          component TEXT PRIMARY KEY,
          weight DOUBLE PRECISION NOT NULL CHECK (weight >= 0)
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_reliability_config (
          doc_type TEXT PRIMARY KEY,
          reliability DOUBLE PRECISION NOT NULL CHECK (reliability >= 0 AND reliability <= 1)
        );
        """
    )

    for component, weight in FALLBACK_WEIGHTS.items():
        await conn.execute(
            """
            INSERT INTO confidence_weights(component, weight)
            VALUES ($1, $2)
            ON CONFLICT (component) DO NOTHING
            """,
            component,
            weight,
        )
    for doc_type, reliability in FALLBACK_SOURCE_RELIABILITY.items():
        await conn.execute(
            """
            INSERT INTO source_reliability_config(doc_type, reliability)
            VALUES ($1, $2)
            ON CONFLICT (doc_type) DO NOTHING
            """,
            doc_type,
            reliability,
        )


async def load_runtime_config(*, force_refresh: bool = False) -> RuntimeConfidenceConfig:
    """Load confidence config from Postgres, fallback to in-process defaults."""
    global _CONFIG_READY, _CONFIG_CACHE
    if _CONFIG_READY and not force_refresh:
        return _CONFIG_CACHE

    async with _config_lock():
        if _CONFIG_READY and not force_refresh:
            return _CONFIG_CACHE
        try:
            p = await _pool()
            async with p.acquire() as conn:
                await _ensure_config_tables(conn)
                weight_rows = await conn.fetch("SELECT component, weight FROM confidence_weights")
                source_rows = await conn.fetch("SELECT doc_type, reliability FROM source_reliability_config")

            db_weights = {str(r["component"]): float(r["weight"]) for r in weight_rows}
            db_source = {str(r["doc_type"]).lower(): float(r["reliability"]) for r in source_rows}
            _CONFIG_CACHE = RuntimeConfidenceConfig(
                weights=db_weights or dict(FALLBACK_WEIGHTS),
                source_reliability=db_source or dict(FALLBACK_SOURCE_RELIABILITY),
            )
            _CONFIG_READY = True
        except Exception:
            # Сохраняем работоспособность даже если БД временно недоступна.
            if not _CONFIG_READY:
                _CONFIG_CACHE = RuntimeConfidenceConfig(
                    weights=dict(FALLBACK_WEIGHTS),
                    source_reliability=dict(FALLBACK_SOURCE_RELIABILITY),
                )
    return _CONFIG_CACHE


def _runtime_config() -> RuntimeConfidenceConfig:
    return _CONFIG_CACHE


def source_reliability(doc_type: str | None, *, verified: bool = False,
                       trusted_org: bool = False) -> float:
    config = _runtime_config()
    base = config.source_reliability.get((doc_type or "").lower(), 0.5)
    if verified:
        base += 0.10
    if trusted_org:
        base += 0.05
    return min(base, 1.0)


def corroboration(n_independent_sources: int, k: float = 0.7) -> float:
    """Насыщающаяся функция: 3–4 источника дают высокий вклад."""
    return 1.0 - math.exp(-k * max(n_independent_sources, 0))


def consistency(n_open_contradictions: int) -> float:
    return 1.0 / (1.0 + max(n_open_contradictions, 0))


def recency(years_old: float, half_life: float = 8.0) -> float:
    """Экспоненциальное затухание свежести (период полураспада ~8 лет)."""
    return 0.5 ** (max(years_old, 0.0) / half_life)


def compute(components: dict[str, float],
            weights: dict[str, float] | None = None) -> ConfidenceBreakdown:
    w = weights or _runtime_config().weights
    total_w = sum(w.values()) or 1.0
    score = sum(w[k] * components.get(k, 0.0) for k in w) / total_w
    return ConfidenceBreakdown(
        confidence=round(score, 4),
        components={k: components.get(k, 0.0) for k in w},
        weights=w,
    )
