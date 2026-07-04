"""Помощник очереди arq: enqueue задач из gateway в worker (через Redis)."""
from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from mkg_core.config import get_settings


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def enqueue(function: str, *args: Any, **kwargs: Any) -> str | None:
    """Поставить задачу в очередь. Возвращает job_id или None при недоступности Redis."""
    try:
        pool = await create_pool(redis_settings())
        job = await pool.enqueue_job(function, *args, **kwargs)
        return job.job_id if job else None
    except Exception:
        return None


async def abort_job(job_id: str | None) -> bool:
    """Попытка прервать задачу arq (дополнение к cooperative cancel через флаг)."""
    if not job_id:
        return False
    try:
        from arq.jobs import Job

        pool = await create_pool(redis_settings())
        job = Job(job_id, pool)
        await job.abort()
        return True
    except Exception:
        return False
