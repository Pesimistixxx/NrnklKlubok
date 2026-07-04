"""MKG Worker (arq): очередь ingestion + extraction."""
from __future__ import annotations

import os

from mkg_core.logging import setup_logging
from mkg_core.queue import redis_settings

from app.tasks import run_extraction, run_ingestion

setup_logging("worker")


class WorkerSettings:
    functions = [run_ingestion, run_extraction]
    redis_settings = redis_settings()
    max_jobs = int(os.getenv("WORKER_MAX_JOBS", "1"))
    job_timeout = 600
