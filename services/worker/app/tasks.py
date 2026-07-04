"""Задачи arq: ingestion и extraction документа."""

from __future__ import annotations



import logging

from typing import Any



from mkg_core import build_marked_markdown, get_settings, set_doc_context, update_document_status, upsert_document

from mkg_core.logging import setup_logging

from mkg_core.queue import enqueue

from mkg_core.runtime_config import get_llm_model, load_runtime_config

from mkg_core.store import get_repo

from mkg_extraction import ExtractionCancelled, extract_from_markdown, load_graph

from mkg_ingestion import process

from mkg_ingestion.formats import mime_type



log = setup_logging("worker")





async def _configure_llm() -> str:

    model = await get_llm_model()

    settings = get_settings()

    try:

        from mkg_prompts import PromptRegistry



        PromptRegistry.configure(settings.prompts_path, model=model)

    except Exception as exc:

        log.warning("PromptRegistry недоступен: %s", exc)

    return model





async def run_ingestion(ctx: dict[str, Any], document_id: str) -> dict[str, Any]:

    set_doc_context(document_id)
    await load_runtime_config()

    llm_model = await _configure_llm()

    log.info("ingestion start doc_id=%s llm=%s", document_id, llm_model)



    repo = get_repo()

    rec = repo.get(document_id)

    if not rec:

        log.error("ingestion doc not found doc_id=%s", document_id)

        return {"document_id": document_id, "status": "failed", "error": "not found"}



    repo.set_status(document_id, "processing", step="ingestion")

    try:

        await upsert_document(repo.get(document_id) or rec)

        await update_document_status(document_id, "processing", step="ingestion")

    except Exception as exc:

        log.warning("postgres update failed ingestion start: %s", exc)



    content = repo.read_source(document_id) or b""

    file_name = rec["file_name"]

    doc_route = rec.get("doc_type") or mime_type(file_name)



    try:

        result = await process(document_id, file_name, content)

        repo.save_markdown(document_id, result.markdown)
        if result.raw_markdown:
            repo.save_raw_markdown(document_id, result.raw_markdown)
        repo.save_marked_markdown(
            document_id,
            build_marked_markdown(document_id, result.markdown, None),
        )

        repo.set_status(

            document_id,

            "md_ready",

            lang=result.lang,

            doc_type=result.doc_type or doc_route,

            step="ingestion_done",

            error=None,

        )

        try:

            await update_document_status(

                document_id,

                "md_ready",

                lang=result.lang,

                doc_type=result.doc_type or doc_route,

                step="ingestion_done",

                error=None,

            )

        except Exception as exc:

            log.warning("postgres update failed ingestion done: %s", exc)



        log.info(

            "ingestion done doc_id=%s chunks=%s lang=%s",

            document_id,

            len(result.chunks),

            result.lang,

        )



        from mkg_core.post_ingest import after_ingestion_done

        await after_ingestion_done(document_id)



        return {

            "document_id": document_id,

            "status": "md_ready",

            "doc_type": result.doc_type,

            "chunks": len(result.chunks),

        }

    except Exception as exc:

        log.exception("ingestion failed doc_id=%s", document_id)

        repo.set_status(document_id, "failed", error=str(exc), step="ingestion_failed")

        try:

            await update_document_status(document_id, "failed", error=str(exc), step="ingestion_failed")

        except Exception:

            pass

        return {"document_id": document_id, "status": "failed", "error": str(exc)}





async def run_extraction(ctx: dict[str, Any], document_id: str) -> dict[str, Any]:
    from mkg_core.document_extraction import run_document_extraction

    return await run_document_extraction(document_id)

