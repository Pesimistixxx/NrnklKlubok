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

    set_doc_context(document_id)
    await load_runtime_config()

    llm_model = await _configure_llm()

    log.info("extraction start doc_id=%s llm=%s", document_id, llm_model)

    repo = get_repo()

    if not repo.get(document_id):
        return {"document_id": document_id, "status": "failed", "error": "not found"}

    if repo.is_cancel_requested(document_id):
        repo.clear_cancel_extraction(document_id)
        repo.set_status(document_id, "md_ready", step="extraction_cancelled", error=None)
        try:
            await update_document_status(document_id, "md_ready", step="extraction_cancelled", error=None)
        except Exception:
            pass
        return {"document_id": document_id, "status": "md_ready", "cancelled": True}

    repo.clear_cancel_extraction(document_id)
    repo.delete_graph(document_id)
    repo.set_status(document_id, "extracting", step="extraction", graph_nodes=0, graph_relationships=0)

    try:
        await update_document_status(document_id, "extracting", step="extraction")
    except Exception as exc:
        log.warning("postgres update failed extraction start: %s", exc)

    markdown = repo.read_markdown(document_id)

    if not markdown:
        repo.set_status(document_id, "failed", error="markdown not ready", step="extraction_failed")
        return {"document_id": document_id, "status": "failed", "error": "markdown not ready"}

    rec = repo.get(document_id) or {}

    try:
        payload = (
            await extract_from_markdown(
                document_id,
                markdown,
                file_name=rec.get("file_name", ""),
                classification=rec.get("classification", "открытый"),
                lang=rec.get("lang"),
            )
        ).as_dict()
    except ExtractionCancelled:
        log.info("extraction cancelled doc_id=%s", document_id)
        repo.delete_graph(document_id)
        repo.clear_cancel_extraction(document_id)
        repo.save_marked_markdown(
            document_id,
            build_marked_markdown(document_id, markdown, None),
        )
        repo.set_status(
            document_id,
            "md_ready",
            step="extraction_cancelled",
            error=None,
            graph_nodes=0,
            graph_relationships=0,
            neo4j_synced=False,
        )
        try:
            await update_document_status(
                document_id,
                "md_ready",
                step="extraction_cancelled",
                error=None,
                graph_nodes=0,
                graph_relationships=0,
                neo4j_synced=False,
            )
        except Exception:
            pass
        return {"document_id": document_id, "status": "md_ready", "cancelled": True}

    node_count = len(payload.get("nodes", []))

    rel_count = len(payload.get("relationships", []))

    repo.save_graph(document_id, payload)

    repo.save_marked_markdown(
        document_id,
        build_marked_markdown(document_id, markdown, payload),
    )

    log.info("graph payload saved doc_id=%s nodes=%s rels=%s", document_id, node_count, rel_count)



    if node_count == 0:

        repo.set_status(document_id, "failed", error="пустой граф после extraction", step="extraction_empty")

        try:

            await update_document_status(document_id, "failed", error="пустой граф после extraction", step="extraction_empty")

        except Exception:

            pass

        return {"document_id": document_id, "status": "failed", "error": "пустой граф после extraction"}



    sync = {"nodes": 0, "relationships": 0}

    neo4j_synced = False

    neo4j_error = None

    if repo.is_cancel_requested(document_id):
        repo.delete_graph(document_id)
        repo.clear_cancel_extraction(document_id)
        repo.save_marked_markdown(
            document_id,
            build_marked_markdown(document_id, markdown, None),
        )
        repo.set_status(
            document_id,
            "md_ready",
            step="extraction_cancelled",
            error=None,
            graph_nodes=0,
            graph_relationships=0,
            neo4j_synced=False,
        )
        try:
            await update_document_status(
                document_id,
                "md_ready",
                step="extraction_cancelled",
                graph_nodes=0,
                graph_relationships=0,
                neo4j_synced=False,
            )
        except Exception:
            pass
        return {"document_id": document_id, "status": "md_ready", "cancelled": True}

    try:

        repo.set_status(document_id, "extracting", step="neo4j_load")

        sync = await load_graph(payload)

        neo4j_synced = True

        log.info("neo4j synced doc_id=%s nodes=%s rels=%s", document_id, sync["nodes"], sync["relationships"])

    except Exception as exc:

        neo4j_synced = False

        neo4j_error = str(exc)

        log.error("neo4j load failed doc_id=%s: %s", document_id, exc)



    final_status = "loaded" if neo4j_synced else "md_ready"

    final_step = "done" if neo4j_synced else "graph_local"



    repo.set_status(

        document_id,

        final_status,

        neo4j_synced=neo4j_synced,

        graph_nodes=node_count,

        graph_relationships=rel_count,

        step=final_step,

        error=neo4j_error,

        neo4j_error=neo4j_error,

    )

    try:

        await update_document_status(

            document_id,

            final_status,

            neo4j_synced=neo4j_synced,

            graph_nodes=node_count,

            graph_relationships=rel_count,

            step=final_step,

            error=neo4j_error,

        )

    except Exception as exc:

        log.warning("postgres update failed extraction done: %s", exc)



    l4_stats: dict[str, Any] = {}

    if node_count > 0:

        try:

            repo.set_status(document_id, final_status, step="qdrant_index")

            try:

                await update_document_status(document_id, final_status, step="qdrant_index")

            except Exception as exc:

                log.warning("postgres update failed qdrant_index start: %s", exc)

            from mkg_core.embeddings import index_document_graph

            await index_document_graph(document_id, payload)

            log.info("qdrant indexed doc_id=%s", document_id)

        except Exception as exc:

            log.warning("qdrant index failed doc_id=%s: %s", document_id, exc)

        else:
            mode = (repo.get(document_id) or rec).get("processing_mode") or "full"
            if mode != "answers_only":
                try:
                    from mkg_core.l4_clustering import apply_document_l4_cluster

                    l4_stats = await apply_document_l4_cluster(document_id)
                    log.info("l4 clustered doc_id=%s stats=%s", document_id, l4_stats)
                except Exception as exc:
                    log.warning("l4 cluster failed doc_id=%s: %s", document_id, exc)



    return {

        "document_id": document_id,

        "status": final_status,

        "neo4j_synced": neo4j_synced,

        "graph_nodes": node_count,

        "graph_relationships": rel_count,

        "synced_nodes": sync["nodes"],

        "synced_relationships": sync["relationships"],

        "neo4j_error": neo4j_error,

        "l4": l4_stats,

    }

