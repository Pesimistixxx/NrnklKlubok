"""Действия после успешного ingestion (OCR → Markdown)."""
from __future__ import annotations

import logging
from typing import Literal

from mkg_core.config import get_settings
from mkg_core.meta_db import update_document_status
from mkg_core.queue import enqueue
from mkg_core.store import get_repo

log = logging.getLogger(__name__)

ProcessingMode = Literal["full", "answers_only"]


async def after_ingestion_done(document_id: str) -> None:
    """Полный пайплайн (extraction) или лёгкий путь (только Qdrant из MD)."""
    repo = get_repo()
    rec = repo.get(document_id) or {}
    mode: ProcessingMode = rec.get("processing_mode") or "full"

    if mode == "answers_only":
        from mkg_core.embeddings import index_document_markdown

        markdown = repo.read_markdown(document_id) or ""
        try:
            stats = await index_document_markdown(document_id, markdown)
            repo.set_status(
                document_id,
                "loaded",
                step="answers_indexed",
                graph_nodes=0,
                graph_relationships=0,
                neo4j_synced=False,
                error=None,
            )
            try:
                await update_document_status(
                    document_id,
                    "loaded",
                    step="answers_indexed",
                    graph_nodes=0,
                    graph_relationships=0,
                    neo4j_synced=False,
                    error=None,
                )
            except Exception as exc:
                log.warning("postgres update failed answers_indexed: %s", exc)
            log.info(
                "answers_only indexed doc_id=%s chunks=%s",
                document_id,
                stats.get("indexed", 0),
            )
        except Exception as exc:
            log.exception("answers_only index failed doc_id=%s", document_id)
            repo.set_status(document_id, "failed", error=str(exc), step="index_failed")
            try:
                await update_document_status(document_id, "failed", error=str(exc), step="index_failed")
            except Exception:
                pass
        return

    settings = get_settings()
    if not settings.auto_extract_after_ingest:
        return

    job_id = await enqueue("run_extraction", document_id)
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
