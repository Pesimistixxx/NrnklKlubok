"""Планирование extraction: очередь worker или inline fallback в gateway."""
from __future__ import annotations

import logging

from mkg_core.meta_db import update_document_status
from mkg_core.queue import enqueue
from mkg_core.store import get_repo

log = logging.getLogger(__name__)


async def schedule_document_extraction(document_id: str, *, inline_fallback: bool = True) -> dict[str, str]:
    """Поставить extraction в очередь; при недоступности Redis — выполнить inline."""
    repo = get_repo()
    if not repo.get(document_id):
        return {"document_id": document_id, "status": "failed", "mode": "missing"}

    repo.clear_cancel_extraction(document_id)
    job_id = await enqueue("run_extraction", document_id)
    if job_id:
        repo.set_status(
            document_id,
            "extracting",
            step="extraction",
            extraction_job_id=job_id,
            cancel_requested=False,
        )
        try:
            await update_document_status(document_id, "extracting", step="extraction")
        except Exception as exc:
            log.warning("postgres update failed extraction schedule: %s", exc)
        return {"document_id": document_id, "status": "extracting", "job_id": job_id, "mode": "queue"}

    if not inline_fallback:
        log.error("extraction queue unavailable doc_id=%s", document_id)
        return {"document_id": document_id, "status": "md_ready", "mode": "queue_failed"}

    log.warning("Redis/worker queue unavailable — inline extraction doc_id=%s", document_id)
    from mkg_core.document_extraction import run_document_extraction

    result = await run_document_extraction(document_id)
    return {
        "document_id": document_id,
        "status": str(result.get("status", "unknown")),
        "mode": "inline",
    }
