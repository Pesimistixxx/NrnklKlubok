"""Полный цикл extraction → Neo4j → Qdrant → L4 (общий для worker и gateway)."""
from __future__ import annotations

import logging
from typing import Any

from mkg_core import build_marked_markdown, get_settings, set_doc_context, update_document_status
from mkg_core.runtime_config import get_llm_model, load_runtime_config
from mkg_core.store import get_repo
from mkg_extraction import ExtractionCancelled, extract_from_markdown, load_graph

log = logging.getLogger(__name__)


async def _configure_llm() -> str:
    model = await get_llm_model()
    settings = get_settings()
    try:
        from mkg_prompts import PromptRegistry

        PromptRegistry.configure(settings.prompts_path, model=model)
    except Exception as exc:
        log.warning("prompt registry configure failed: %s", exc)
    return model


async def run_document_extraction(document_id: str) -> dict[str, Any]:
    """Извлечь граф из Markdown, синхронизировать Neo4j и проиндексировать Qdrant."""
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
        repo.save_marked_markdown(document_id, build_marked_markdown(document_id, markdown, None))
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
    repo.save_marked_markdown(document_id, build_marked_markdown(document_id, markdown, payload))
    log.info("graph payload saved doc_id=%s nodes=%s rels=%s", document_id, node_count, rel_count)

    if node_count == 0:
        repo.set_status(document_id, "failed", error="пустой граф после extraction", step="extraction_empty")
        try:
            await update_document_status(
                document_id, "failed", error="пустой граф после extraction", step="extraction_empty"
            )
        except Exception:
            pass
        return {"document_id": document_id, "status": "failed", "error": "пустой граф после extraction"}

    sync = {"nodes": 0, "relationships": 0}
    neo4j_synced = False
    neo4j_error = None
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
    index_stats: dict[str, Any] = {}
    if node_count > 0:
        try:
            repo.set_status(document_id, final_status, step="qdrant_index")
            try:
                await update_document_status(document_id, final_status, step="qdrant_index")
            except Exception as exc:
                log.warning("postgres update failed qdrant_index start: %s", exc)
            from mkg_core.embeddings import index_document_graph

            index_stats = await index_document_graph(document_id, payload)
            log.info(
                "qdrant indexed doc_id=%s l3=%s l4=%s total=%s",
                document_id,
                index_stats.get("indexed_l3", 0),
                index_stats.get("indexed_l4", 0),
                index_stats.get("indexed", 0),
            )
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
        "index": index_stats,
        "l4": l4_stats,
    }
