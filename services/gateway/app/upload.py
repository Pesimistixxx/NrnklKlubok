"""Общая логика приёма файлов (gateway)."""
from __future__ import annotations

from typing import Any

from mkg_core import get_settings, upsert_document
from mkg_core.doc_metadata import prepare_upload_metadata
from mkg_core.queue import enqueue
from mkg_ingestion.formats import detect_route, mime_type, validate_upload

from app.storage import get_repo


async def accept_upload(
    file_name: str,
    content: bytes,
    *,
    classification: str = "открытый",
    processing_mode: str = "full",
    source_location: str | None = None,
    geography: str | None = None,
    material_date: str | None = None,
    enqueue_ingestion: bool = True,
) -> dict[str, Any]:
    """Сохранить файл, поставить ingestion в очередь, синхронизировать Postgres."""
    settings = get_settings()
    validate_upload(file_name, len(content), max_bytes=settings.max_upload_bytes)

    mode = processing_mode if processing_mode in ("full", "answers_only") else "full"
    meta = prepare_upload_metadata(
        source_location=source_location,
        geography=geography,
        material_date=material_date,
    )
    rec = get_repo().create(
        file_name,
        content,
        classification=classification,
        organization=None,
        processing_mode=mode,
        **meta,
    )
    rec["doc_type"] = detect_route(file_name)
    rec["mime_type"] = mime_type(file_name)
    get_repo().set_status(rec["id"], rec["status"], doc_type=rec["doc_type"], mime_type=rec["mime_type"])

    job_id = None
    if enqueue_ingestion and rec["status"] == "uploaded":
        job_id = await enqueue("run_ingestion", rec["id"])

    try:
        await upsert_document(rec)
    except Exception:
        pass

    return {**rec, "job_id": job_id}
