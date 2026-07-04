"""MKG Gateway — FastAPI: upload, pipeline L1–L6, Neo4j/Qdrant/L4, UI, Agent API.

REST: /api/v1/documents, /graph, /chat, /query, /agents, /agents-service.
"""
from __future__ import annotations

import time
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from mkg_core import (
    Neo4jClient,
    build_marked_markdown,
    clear_all_documents,
    get_document as db_get_document,
    list_documents as db_list_documents,
    public_config,
    read_logs,
    run_diagnostics,
    set_config,
    set_doc_context,
    setup_logging,
    update_document_status,
    upsert_document,
)
from mkg_core.meta_db import count_restricted_documents as db_count_restricted_documents
from mkg_core.config import get_settings
from mkg_core.queue import enqueue, abort_job
from mkg_core.layer_pipeline import build_layer_pipeline
from mkg_core.llm_cache import LLMResponseCache
from mkg_ingestion.formats import formats_public, is_binary
from mkg_ingestion import process as run_ingestion_process
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.ontology import LABEL_LAYER, NODE_PROP_HINTS, NODE_PROP_UI_REQUIRED, describe_relationship_type, sanitize_graph_payload

from app.agent_api import router as agent_router
from app.agents_proxy import router as agents_proxy_router
from app.collab_api import router as collab_router
from app.compare_api import router as compare_router
from app.dashboard_api import router as dashboard_router
from app.data_access import allowed_classifications, assert_document_access
from app.data_access_api import router as data_access_router
from app.docs_api import router as docs_router
from app.graph_anomalies import router as graph_anomalies_router
from app.request_context import role_from_request
from app.search_api import router as search_router
from app.schemas import (
    BatchUploadItem,
    BatchUploadOut,
    DiagnosticsOut,
    DocStatus,
    DocumentList,
    DocumentOut,
    FormatsOut,
    GraphNode,
    GraphOut,
    GraphRelationship,
    GraphRelationshipDetailOut,
    GraphRelationshipPatchIn,
    GraphRelationshipPatchOut,
    LayerPipelineOut,
    PipelineLogOut,
    ClearDatabaseOut,
    ReindexCorpusOut,
    ReindexEntitiesOut,
    RuntimeConfigOut,
    RuntimeConfigUpdate,
)
from app.storage import get_repo
from app.upload import accept_upload
from app.roles import get_role

_GRAPH_EDIT_ROLES = frozenset({"admin", "engineer"})

log = setup_logging("gateway")
STATIC_DIR = Path(__file__).parent / "static"
API = "/api/v1"

app = FastAPI(
    title="MKG Gateway",
    version="0.4.0",
    description=(
        "Gateway MKG: upload (full|answers_only), pipeline OCR→MD→L1–L6→Neo4j→Qdrant→L4 HDBSCAN, "
        "чат dual search, LangGraph proxy. Agent API: `/api/v1/agents/`. "
        "Docs: Docs/21_pipeline_and_layers.md, Docs/22_chat_agents.md"
    ),
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(docs_router, prefix=API)
app.include_router(agent_router, prefix=API)
app.include_router(collab_router, prefix=API)
app.include_router(agents_proxy_router, prefix=API)
app.include_router(graph_anomalies_router, prefix=API)
app.include_router(dashboard_router, prefix=API)
app.include_router(compare_router, prefix=API)
app.include_router(search_router, prefix=API)
app.include_router(data_access_router, prefix=API)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    elif not request.url.path.startswith("/static"):
        log.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, ms)
    return response


def _merge_repo(rec: dict) -> dict:
    repo_rec = get_repo().get(rec.get("id", ""))
    if not repo_rec:
        return rec
    merged = {**rec}
    for key in (
        "status",
        "doc_type",
        "mime_type",
        "step",
        "error",
        "neo4j_synced",
        "graph_nodes",
        "graph_relationships",
        "lang",
        "neo4j_error",
        "processing_mode",
        "l4_clusters",
        "l4_anomalies",
        "l4_clustered",
        "l4_points",
        "l4_error",
        "source_location",
        "geography",
        "material_date",
        "tags",
        "ingested_at",
    ):
        if repo_rec.get(key) is not None:
            merged[key] = repo_rec[key]
    graph = get_repo().read_graph(rec["id"]) or {}
    if not merged.get("graph_nodes") and graph.get("nodes"):
        merged["graph_nodes"] = len(graph["nodes"])
    if not merged.get("graph_relationships") and graph.get("relationships"):
        merged["graph_relationships"] = len(graph["relationships"])
    return merged


def _graph_stats(doc_id: str, rec: dict) -> tuple[int, int, bool | None]:
    graph = get_repo().read_graph(doc_id) or {}
    nodes = rec.get("graph_nodes")
    rels = rec.get("graph_relationships")
    if nodes is None:
        nodes = len(graph.get("nodes", []))
    if rels is None:
        rels = len(graph.get("relationships", []))
    return int(nodes or 0), int(rels or 0), rec.get("neo4j_synced")


async def _document_access(role_id: str) -> list[str]:
    return await allowed_classifications(role_id)


async def _restricted_document_count(
    allowed: list[str],
    *,
    geography: str | None = None,
    material_year: int | None = None,
) -> int:
    try:
        return await db_count_restricted_documents(
            geography=geography,
            material_year=material_year,
            allowed_classifications=allowed,
        )
    except Exception:
        return get_repo().count_restricted(
            geography=geography,
            material_year=material_year,
            allowed_classifications=allowed,
        )


async def _load_document_record(doc_id: str) -> dict | None:
    rec = None
    try:
        rec = await db_get_document(doc_id)
    except Exception:
        rec = None
    if not rec:
        rec = get_repo().get(doc_id)
    return rec


def _to_out(rec: dict) -> DocumentOut:
    rec = _merge_repo(rec)
    upload_date = rec.get("upload_date")
    if upload_date is None:
        upload_date = "1970-01-01T00:00:00+00:00"
    status_raw = rec.get("status", "uploaded")
    try:
        status = DocStatus(status_raw)
    except ValueError:
        status = DocStatus.uploaded
    return DocumentOut(
        id=rec["id"],
        file_name=rec["file_name"],
        doc_type=rec.get("doc_type"),
        mime_type=rec.get("mime_type"),
        classification=rec.get("classification", "открытый"),
        organization=rec.get("organization"),
        hash_sum=rec["hash_sum"],
        status=status,
        upload_date=upload_date,
        size_bytes=rec["size_bytes"],
        step=rec.get("step"),
        error=rec.get("error") or rec.get("neo4j_error"),
        neo4j_synced=rec.get("neo4j_synced"),
        graph_nodes=rec.get("graph_nodes"),
        graph_relationships=rec.get("graph_relationships"),
        processing_mode=rec.get("processing_mode") or "full",
        l4_clusters=rec.get("l4_clusters"),
        l4_anomalies=rec.get("l4_anomalies"),
        l4_clustered=rec.get("l4_clustered"),
        source_location=rec.get("source_location"),
        geography=rec.get("geography"),
        material_date=_parse_material_date(rec.get("material_date")),
        tags=_parse_tags(rec.get("tags")),
        ingested_at=_parse_datetime(rec.get("ingested_at")),
    )


def _parse_material_date(value: Any):
    if not value:
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value
    try:
        from datetime import date as date_cls

        return date_cls.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value if x]
    return [str(value)]


def _parse_datetime(value: Any):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def _run_ingestion_inline(doc_id: str) -> None:
    set_doc_context(doc_id)
    repo = get_repo()
    rec = repo.get(doc_id)
    if not rec:
        return
    log.info("inline ingestion start doc_id=%s", doc_id)
    repo.set_status(doc_id, DocStatus.processing.value, step="ingestion")
    try:
        await update_document_status(doc_id, DocStatus.processing.value, step="ingestion")
    except Exception as exc:
        log.warning("postgres: %s", exc)
    content = repo.read_source(doc_id) or b""
    try:
        result = await run_ingestion_process(doc_id, rec["file_name"], content)
        repo.save_markdown(doc_id, result.markdown)
        if result.raw_markdown:
            repo.save_raw_markdown(doc_id, result.raw_markdown)
        repo.save_marked_markdown(
            doc_id,
            build_marked_markdown(doc_id, result.markdown, None),
        )
        repo.set_status(
            doc_id,
            DocStatus.md_ready.value,
            lang=result.lang,
            doc_type=result.doc_type,
            step="ingestion_done",
        )
        await update_document_status(
            doc_id,
            DocStatus.md_ready.value,
            lang=result.lang,
            doc_type=result.doc_type,
            step="ingestion_done",
        )
        log.info("inline ingestion done doc_id=%s", doc_id)
        from mkg_core.post_ingest import after_ingestion_done

        await after_ingestion_done(doc_id)
    except Exception as exc:
        log.exception("inline ingestion failed doc_id=%s", doc_id)
        repo.set_status(doc_id, DocStatus.failed.value, error=str(exc))
        try:
            await update_document_status(doc_id, DocStatus.failed.value, error=str(exc))
        except Exception:
            pass


async def _run_neo4j_sync_inline(doc_id: str) -> None:
    """Повторная синхронизация локального графа в Neo4j."""
    from mkg_extraction import load_graph

    set_doc_context(doc_id)
    repo = get_repo()
    rec = repo.get(doc_id)
    if not rec:
        return
    graph = repo.read_graph(doc_id)
    if not graph or not graph.get("nodes"):
        repo.set_status(doc_id, DocStatus.failed.value, error="граф не найден", step="neo4j_load")
        return
    try:
        sync = await load_graph(graph)
        repo.set_status(
            doc_id,
            DocStatus.loaded.value,
            neo4j_synced=True,
            step="done",
            error=None,
            neo4j_error=None,
        )
        try:
            await update_document_status(
                doc_id,
                DocStatus.loaded.value,
                neo4j_synced=True,
                step="done",
                error=None,
            )
        except Exception as exc:
            log.warning("postgres update failed neo4j sync: %s", exc)
        log.info("neo4j re-synced doc_id=%s nodes=%s rels=%s", doc_id, sync["nodes"], sync["relationships"])
    except Exception as exc:
        log.exception("neo4j re-sync failed doc_id=%s", doc_id)
        repo.set_status(
            doc_id,
            DocStatus.failed.value,
            error=str(exc),
            step="neo4j_load",
            neo4j_error=str(exc),
        )
        try:
            await update_document_status(doc_id, DocStatus.failed.value, error=str(exc), step="neo4j_load")
        except Exception:
            pass


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(f"{API}/diagnostics", response_model=DiagnosticsOut)
async def diagnostics() -> DiagnosticsOut:
    return DiagnosticsOut(**await run_diagnostics())


@app.get(f"{API}/config/models", response_model=RuntimeConfigOut)
async def get_models_config() -> RuntimeConfigOut:
    return RuntimeConfigOut(**await public_config())


@app.put(f"{API}/config/models", response_model=RuntimeConfigOut)
async def update_models_config(body: RuntimeConfigUpdate) -> RuntimeConfigOut:
    values = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        await set_config(values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log.info("runtime config updated: %s", values)
    return RuntimeConfigOut(**await public_config())


@app.get(f"{API}/formats", response_model=FormatsOut)
async def get_formats() -> FormatsOut:
    return FormatsOut(**formats_public())


@app.get(f"{API}/ontology/node-fields")
async def get_node_field_hints() -> dict[str, Any]:
    """Ожидаемые props по метке узла — для UI и проверки extraction."""
    return {
        label: {
            "fields": list(fields),
            "required": list(NODE_PROP_UI_REQUIRED.get(label, fields)),
        }
        for label, fields in NODE_PROP_HINTS.items()
    }


@app.post(f"{API}/documents", response_model=DocumentOut)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    classification: str = Form("открытый"),
    processing_mode: str = Form("full"),
    source_location: str | None = Form(None),
    geography: str | None = Form(None),
    material_date: str | None = Form(None),
) -> DocumentOut:
    content = await file.read()
    try:
        rec = await accept_upload(
            file.filename or "unnamed",
            content,
            classification=classification,
            processing_mode=processing_mode,
            source_location=source_location,
            geography=geography,
            material_date=material_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if rec.get("job_id") is None and rec["status"] == DocStatus.uploaded.value:
        background.add_task(_run_ingestion_inline, rec["id"])
    return _to_out(rec)


@app.post(f"{API}/documents/batch", response_model=BatchUploadOut)
async def upload_documents_batch(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    classification: str = Form("открытый"),
    processing_mode: str = Form("full"),
    source_location: str | None = Form(None),
    geography: str | None = Form(None),
    material_date: str | None = Form(None),
) -> BatchUploadOut:
    if not files:
        raise HTTPException(status_code=400, detail="Не переданы файлы")
    items: list[BatchUploadItem] = []
    uploaded = failed = 0
    for file in files:
        name = file.filename or "unnamed"
        content = await file.read()
        try:
            rec = await accept_upload(
                name,
                content,
                classification=classification,
                processing_mode=processing_mode,
                source_location=source_location,
                geography=geography,
                material_date=material_date,
            )
            if rec.get("job_id") is None and rec["status"] == DocStatus.uploaded.value:
                background.add_task(_run_ingestion_inline, rec["id"])
            items.append(BatchUploadItem(file_name=name, document=_to_out(rec)))
            uploaded += 1
        except ValueError as exc:
            items.append(BatchUploadItem(file_name=name, error=str(exc)))
            failed += 1
    return BatchUploadOut(uploaded=uploaded, failed=failed, items=items)


@app.post(f"{API}/documents/{{doc_id}}/reprocess")
async def reprocess_document(doc_id: str, background: BackgroundTasks) -> dict[str, str]:
    """Повтор OCR → Markdown. Всегда переводит документ в полный пайплайн (не answers_only)."""
    if not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    get_repo().set_status(
        doc_id,
        DocStatus.uploaded.value,
        error=None,
        step="reprocess",
        processing_mode="full",
    )
    job_id = await enqueue("run_ingestion", doc_id)
    if job_id is None:
        background.add_task(_run_ingestion_inline, doc_id)
    return {"document_id": doc_id, "status": DocStatus.processing.value, "processing_mode": "full"}


@app.post(f"{API}/documents/{{doc_id}}/reprocess-full")
async def reprocess_full_pipeline(doc_id: str, background: BackgroundTasks) -> dict[str, str]:
    """Полный пайплайн для документа «только для чата»: L1–L6 → граф → Neo4j → Qdrant → L4."""
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    get_repo().set_status(doc_id, rec.get("status", DocStatus.uploaded.value), processing_mode="full")
    md = get_repo().read_markdown(doc_id)
    st = rec.get("status", "")
    if md and st in (DocStatus.md_ready.value, DocStatus.loaded.value, DocStatus.failed.value):
        get_repo().clear_cancel_extraction(doc_id)
        job_id = await enqueue("run_extraction", doc_id)
        get_repo().set_status(
            doc_id,
            DocStatus.extracting.value,
            step="extraction",
            extraction_job_id=job_id,
            cancel_requested=False,
            processing_mode="full",
        )
        try:
            await update_document_status(doc_id, DocStatus.extracting.value, step="extraction")
        except Exception:
            pass
        return {
            "document_id": doc_id,
            "status": DocStatus.extracting.value,
            "processing_mode": "full",
            "job_id": job_id or "",
        }
    get_repo().set_status(
        doc_id,
        DocStatus.uploaded.value,
        error=None,
        step="reprocess_full",
        processing_mode="full",
    )
    job_id = await enqueue("run_ingestion", doc_id)
    if job_id is None:
        background.add_task(_run_ingestion_inline, doc_id)
    return {"document_id": doc_id, "status": DocStatus.processing.value, "processing_mode": "full"}


@app.post(f"{API}/documents/{{doc_id}}/neo4j-sync")
async def sync_document_neo4j(doc_id: str, background: BackgroundTasks) -> dict[str, str]:
    """Повторная загрузка локального графа в Neo4j."""
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    graph = get_repo().read_graph(doc_id)
    if not graph or not graph.get("nodes"):
        raise HTTPException(status_code=409, detail="Локальный граф ещё не сформирован")
    background.add_task(_run_neo4j_sync_inline, doc_id)
    get_repo().set_status(doc_id, DocStatus.extracting.value, error=None, step="neo4j_load")
    return {"document_id": doc_id, "status": DocStatus.extracting.value, "step": "neo4j_load"}


@app.post(f"{API}/documents/{{doc_id}}/index")
async def index_document_vectors(doc_id: str) -> dict[str, Any]:
    """Индексация в Qdrant: из графа или напрямую из Markdown (answers_only)."""
    from mkg_core.embeddings import index_document_graph, index_document_markdown
    from mkg_core.l4_clustering import apply_document_l4_cluster

    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    graph = get_repo().read_graph(doc_id)
    if graph and graph.get("nodes"):
        stats = await index_document_graph(doc_id, graph)
        if (rec.get("processing_mode") or "full") != "answers_only":
            l4 = await apply_document_l4_cluster(doc_id)
            stats = {**stats, "l4": l4}
    else:
        md = get_repo().read_markdown(doc_id)
        if not md:
            raise HTTPException(status_code=409, detail="Markdown ещё не готов")
        stats = await index_document_markdown(doc_id, md)
    return {"document_id": doc_id, **stats}


@app.post(f"{API}/documents/{{doc_id}}/l4-cluster")
async def cluster_document_l4(doc_id: str) -> dict[str, Any]:
    """HDBSCAN L4 после Qdrant — перезапуск этапа кластеризации."""
    from mkg_core.embeddings import index_document_graph
    from mkg_core.l4_clustering import apply_document_l4_cluster

    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if (rec.get("processing_mode") or "full") == "answers_only":
        raise HTTPException(status_code=409, detail="L4 недоступен в режиме answers_only")
    graph = get_repo().read_graph(doc_id)
    if not graph or not graph.get("nodes"):
        raise HTTPException(status_code=409, detail="Граф ещё не сформирован")
    await index_document_graph(doc_id, graph)
    try:
        return await apply_document_l4_cluster(doc_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(f"{API}/documents", response_model=DocumentList)
async def list_documents(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    geography: str | None = None,
    material_year: int | None = None,
) -> DocumentList:
    role_id = role_from_request(request)
    allowed = await _document_access(role_id)
    restricted_count = 0
    try:
        items, total = await db_list_documents(
            page,
            page_size,
            geography=geography,
            material_year=material_year,
            classifications=allowed,
        )
        restricted_count = await _restricted_document_count(
            allowed, geography=geography, material_year=material_year
        )
    except Exception:
        items, total = get_repo().list(
            page,
            page_size,
            geography=geography,
            material_year=material_year,
            classifications=allowed,
        )
        restricted_count = get_repo().count_restricted(
            geography=geography,
            material_year=material_year,
            allowed_classifications=allowed,
        )
    try:
        out_items = [_to_out(r) for r in items]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка сериализации документов: {exc}") from exc
    return DocumentList(
        items=out_items,
        total=total,
        page=page,
        page_size=page_size,
        restricted_count=restricted_count,
    )


@app.get(f"{API}/documents/{{doc_id}}", response_model=DocumentOut)
async def get_document(request: Request, doc_id: str) -> DocumentOut:
    rec = await _load_document_record(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    return _to_out(rec)


@app.get(f"{API}/documents/{{doc_id}}/markdown")
async def get_markdown(
    request: Request,
    doc_id: str,
    variant: str = Query(default="clean", pattern="^(clean|raw|marked)$"),
    download: bool = Query(default=False),
) -> Response:
    rec = await _load_document_record(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    repo = get_repo()
    if variant == "marked":
        md = repo.read_marked_markdown(doc_id)
        if md is None:
            clean = repo.read_markdown(doc_id)
            if clean is None:
                raise HTTPException(status_code=404, detail="Markdown ещё не готов")
            md = build_marked_markdown(doc_id, clean, repo.read_graph(doc_id))
    elif variant == "raw":
        md = repo.read_raw_markdown(doc_id)
        if md is None:
            md = repo.read_markdown(doc_id)
        if md is None:
            raise HTTPException(status_code=404, detail="Markdown ещё не готов")
    else:
        md = repo.read_markdown(doc_id)
        if md is None:
            raise HTTPException(status_code=404, detail="Markdown ещё не готов")
    rec = repo.get(doc_id) or {}
    file_stem = Path(rec.get("file_name") or doc_id).stem
    suffix = {"marked": "marked", "raw": "raw", "clean": "clean"}.get(variant, "clean")
    filename = f"{file_stem}_{suffix}.md"
    headers: dict[str, str] = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )


@app.get(f"{API}/documents/{{doc_id}}/source")
async def get_source(request: Request, doc_id: str) -> Response:
    rec = await _load_document_record(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    raw = get_repo().read_source(doc_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Исходник не найден")
    return Response(content=raw, media_type=rec.get("mime_type") or "application/octet-stream")


@app.post(f"{API}/documents/{{doc_id}}/submit")
async def submit_document(doc_id: str) -> dict[str, str]:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if rec.get("status") not in (DocStatus.md_ready.value, DocStatus.loaded.value, DocStatus.failed.value):
        raise HTTPException(status_code=409, detail="Дождитесь md_ready")
    if (rec.get("processing_mode") or "full") == "answers_only":
        get_repo().set_status(doc_id, rec.get("status"), processing_mode="full")
    get_repo().clear_cancel_extraction(doc_id)
    job_id = await enqueue("run_extraction", doc_id)
    get_repo().set_status(
        doc_id,
        DocStatus.extracting.value,
        step="extraction",
        extraction_job_id=job_id,
        cancel_requested=False,
    )
    try:
        await update_document_status(doc_id, DocStatus.extracting.value, step="extraction")
    except Exception:
        pass
    return {"document_id": doc_id, "status": DocStatus.extracting.value, "job_id": job_id or ""}


@app.post(f"{API}/documents/{{doc_id}}/cancel-extraction")
async def cancel_extraction(doc_id: str) -> dict[str, str]:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if rec.get("status") != DocStatus.extracting.value:
        raise HTTPException(status_code=409, detail="Извлечение не выполняется")
    get_repo().request_cancel_extraction(doc_id)
    await abort_job(rec.get("extraction_job_id"))
    try:
        await update_document_status(doc_id, DocStatus.extracting.value, step="cancelling")
    except Exception:
        pass
    return {"document_id": doc_id, "status": "cancelling"}


@app.get(f"{API}/documents/{{doc_id}}/preview")
async def get_preview(request: Request, doc_id: str) -> dict:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    rec = _merge_repo(rec)
    raw = get_repo().read_source(doc_id) or b""
    file_name = rec.get("file_name", "")
    nodes, rels, neo4j_synced = _graph_stats(doc_id, rec)
    if is_binary(file_name) or raw[:4] == b"%PDF":
        source_kind = "binary"
        source_text = f"бинарный файл · {(len(raw)/1024):.1f} КБ · текст в Markdown после ingestion"
    else:
        source_kind = "text"
        source_text = raw.decode("utf-8", errors="replace")[:20000]
    clean_md = get_repo().read_markdown(doc_id) or ""
    raw_md = get_repo().read_raw_markdown(doc_id) or ""
    repo = get_repo()
    return {
        "document_id": doc_id,
        "status": rec["status"],
        "file_name": file_name,
        "doc_type": rec.get("doc_type"),
        "mime_type": rec.get("mime_type"),
        "classification": rec.get("classification"),
        "organization": rec.get("organization"),
        "hash_sum": rec.get("hash_sum"),
        "size_bytes": rec.get("size_bytes"),
        "upload_date": rec.get("upload_date"),
        "source_location": rec.get("source_location"),
        "geography": rec.get("geography"),
        "material_date": _parse_material_date(rec.get("material_date")),
        "tags": _parse_tags(rec.get("tags")),
        "ingested_at": _parse_datetime(rec.get("ingested_at")),
        "lang": rec.get("lang"),
        "step": rec.get("step"),
        "source_kind": source_kind,
        "source_text": source_text,
        "markdown": clean_md,
        "markdown_raw": raw_md or None,
        "markdown_marked": build_marked_markdown(doc_id, clean_md, get_repo().read_graph(doc_id)),
        "md_file": repo.markdown_relative_path(doc_id) if clean_md else None,
        "md_raw_file": repo.raw_markdown_relative_path(doc_id) if raw_md else None,
        "md_marked_file": repo.marked_markdown_relative_path(doc_id) if clean_md else None,
        "markdown_url": f"{API}/documents/{doc_id}/markdown",
        "error": rec.get("error") or rec.get("neo4j_error"),
        "graph_nodes": nodes,
        "graph_relationships": rels,
        "neo4j_synced": neo4j_synced,
        "processing_mode": rec.get("processing_mode") or "full",
        "l4_clusters": rec.get("l4_clusters"),
        "l4_anomalies": rec.get("l4_anomalies"),
        "l4_clustered": rec.get("l4_clustered"),
        "l4_points": rec.get("l4_points"),
        "l4_error": rec.get("l4_error"),
    }


@app.post(f"{API}/admin/clear", response_model=ClearDatabaseOut)
async def clear_database(confirm: bool = False) -> ClearDatabaseOut:
    if not confirm:
        raise HTTPException(status_code=400, detail="Передайте confirm=true для очистки")
    storage = get_repo().clear_all()
    storage["llm_cache"] = LLMResponseCache.instance().clear_all()
    pg_count = 0
    neo4j_cleared = False
    try:
        pg_count = await clear_all_documents()
    except Exception as exc:
        log.warning("postgres clear failed: %s", exc)
    try:
        await Neo4jClient.instance().clear_all()
        neo4j_cleared = True
    except Exception as exc:
        log.warning("neo4j clear failed: %s", exc)
    log.info("database cleared storage=%s postgres=%s neo4j=%s", storage, pg_count, neo4j_cleared)
    return ClearDatabaseOut(ok=True, storage=storage, postgres_documents=pg_count, neo4j_cleared=neo4j_cleared)


@app.post(f"{API}/admin/reindex-entities", response_model=ReindexEntitiesOut)
async def admin_reindex_entities(
    document_id: str | None = Query(None, description="Один документ или весь корпус"),
) -> ReindexEntitiesOut:
    """Backfill mkg_entities (Material, Process, Equipment, …) для корпуса."""
    from mkg_core.embeddings import reindex_corpus_entities, reindex_document_entities

    if document_id:
        doc_id = document_id if document_id.startswith("doc:") else f"doc:{document_id}"
        if not get_repo().get(doc_id):
            raise HTTPException(status_code=404, detail="Документ не найден")
        stats = await reindex_document_entities(doc_id)
        return ReindexEntitiesOut(
            documents=1,
            indexed=int(stats.get("indexed") or 0),
            skipped=int(stats.get("skipped") or 0),
            collection=str(stats.get("collection") or get_settings().qdrant_collection_entities),
            per_document=[{"document_id": doc_id, **stats}],
        )
    result = await reindex_corpus_entities()
    return ReindexEntitiesOut(**result)


@app.post(f"{API}/admin/reindex", response_model=ReindexCorpusOut)
async def admin_reindex_corpus(
    document_id: str | None = Query(None, description="Один документ или весь корпус"),
) -> ReindexCorpusOut:
    """Полная переиндексация L3+L4+entities в Qdrant."""
    from mkg_core.embeddings import index_document_graph, reindex_corpus

    if document_id:
        doc_id = document_id if document_id.startswith("doc:") else f"doc:{document_id}"
        if not get_repo().get(doc_id):
            raise HTTPException(status_code=404, detail="Документ не найден")
        graph = get_repo().read_graph(doc_id)
        if graph and graph.get("nodes"):
            stats = await index_document_graph(doc_id, graph)
        else:
            from mkg_core.embeddings import index_document_markdown
            md = get_repo().read_markdown(doc_id)
            if not md:
                raise HTTPException(status_code=409, detail="Нет графа и markdown для индексации")
            stats = await index_document_markdown(doc_id, md)
        return ReindexCorpusOut(
            documents=1,
            indexed_l3=int(stats.get("indexed_l3") or stats.get("indexed") or 0),
            indexed_l4=int(stats.get("indexed_l4") or 0),
            indexed_entities=int(stats.get("indexed_entities") or 0),
            skipped=int(stats.get("skipped") or 0),
            per_document=[{"document_id": doc_id, **stats}],
        )
    result = await reindex_corpus()
    return ReindexCorpusOut(**result)


@app.get(f"{API}/documents/{{doc_id}}/logs", response_model=PipelineLogOut)
async def get_document_logs(request: Request, doc_id: str, limit: int = 100) -> PipelineLogOut:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    return PipelineLogOut(document_id=doc_id, items=read_logs(doc_id, limit=limit))


@app.get(f"{API}/graph/documents/{{doc_id}}", response_model=GraphOut)
async def get_document_graph(request: Request, doc_id: str) -> GraphOut:
    rec = await _load_document_record(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    payload = get_repo().read_graph(doc_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Граф ещё не сформирован")
    cleaned = sanitize_graph_payload(
        GraphPayload(
            nodes=list(payload.get("nodes") or []),
            relationships=list(payload.get("relationships") or []),
        )
    ).as_dict()
    nodes = [GraphNode(**n) for n in cleaned.get("nodes", [])]
    relationships = [
        GraphRelationship(
            type=r.get("type", ""),
            from_=r.get("from", ""),
            to=r.get("to", ""),
            props=r.get("props", {}),
        )
        for r in cleaned.get("relationships", [])
    ]
    return GraphOut(document_id=doc_id, nodes=nodes, relationships=relationships)


def _node_layer_label(node: dict[str, Any] | None) -> str:
    if not node:
        return "L?"
    label = str(node.get("label") or "?")
    return LABEL_LAYER.get(label, "L?")


@app.get(
    f"{API}/graph/documents/{{doc_id}}/relationship",
    response_model=GraphRelationshipDetailOut,
)
async def get_document_relationship(
    request: Request,
    doc_id: str,
    from_: str = Query(alias="from"),
    to: str = Query(),
    type: str = Query(),
) -> GraphRelationshipDetailOut:
    rec = await _load_document_record(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    if not from_ or not to or not type:
        raise HTTPException(status_code=400, detail="Параметры from, to и type обязательны")
    payload = get_repo().read_graph(doc_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Граф ещё не сформирован")
    cleaned = dedupe_graph_payload(
        GraphPayload(
            nodes=list(payload.get("nodes") or []),
            relationships=list(payload.get("relationships") or []),
        )
    ).as_dict()
    nodes = cleaned.get("nodes") or []
    rels = cleaned.get("relationships") or []
    node_by_id = {str(n.get("id")): n for n in nodes if n.get("id")}
    match = None
    for rel in rels:
        start = str(rel.get("from") or rel.get("from_") or "")
        end = str(rel.get("to") or "")
        rtype = str(rel.get("type") or "")
        if start == from_ and end == to and rtype == type:
            match = rel
            break
    if not match:
        raise HTTPException(status_code=404, detail="Связь не найдена в графе документа")
    source_raw = node_by_id.get(from_)
    target_raw = node_by_id.get(to)
    source_node = GraphNode(**source_raw) if source_raw else None
    target_node = GraphNode(**target_raw) if target_raw else None
    related: list[GraphRelationship] = []
    seen: set[tuple[str, str, str]] = {(from_, type, to)}
    for rel in rels:
        start = str(rel.get("from") or rel.get("from_") or "")
        end = str(rel.get("to") or "")
        rtype = str(rel.get("type") or "")
        key = (start, rtype, end)
        if key in seen:
            continue
        if start in {from_, to} or end in {from_, to}:
            seen.add(key)
            related.append(
                GraphRelationship(
                    type=rtype,
                    from_=start,
                    to=end,
                    props=rel.get("props") or {},
                )
            )
        if len(related) >= 12:
            break
    return GraphRelationshipDetailOut(
        document_id=doc_id,
        type=type,
        from_=from_,
        to=to,
        props=match.get("props") or {},
        layer=_node_layer_label(source_raw),
        description=describe_relationship_type(type),
        source_node=source_node,
        target_node=target_node,
        related_edges=related,
    )


@app.patch(
    f"{API}/graph/documents/{{doc_id}}/relationship",
    response_model=GraphRelationshipPatchOut,
)
async def patch_document_relationship(
    doc_id: str,
    body: GraphRelationshipPatchIn,
    from_: str = Query(alias="from"),
    to: str = Query(),
    type: str = Query(),
) -> GraphRelationshipPatchOut:
    """Expert comment on graph edge (admin/engineer). Persists in JSON graph + Neo4j props."""
    role = get_role(body.role_id)
    if not role or body.role_id not in _GRAPH_EDIT_ROLES:
        raise HTTPException(status_code=403, detail="Редактирование связей доступно ролям admin и engineer")
    if not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    if not from_ or not to or not type:
        raise HTTPException(status_code=400, detail="Параметры from, to и type обязательны")

    repo = get_repo()
    payload = repo.read_graph(doc_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Граф ещё не сформирован")

    from datetime import datetime, timezone

    edited_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    editor = (body.edited_by or role.get("name_ru") or body.role_id).strip()
    match_idx = None
    rels = list(payload.get("relationships") or [])
    for idx, rel in enumerate(rels):
        start = str(rel.get("from") or rel.get("from_") or "")
        end = str(rel.get("to") or "")
        rtype = str(rel.get("type") or "")
        if start == from_ and end == to and rtype == type:
            match_idx = idx
            break
    if match_idx is None:
        raise HTTPException(status_code=404, detail="Связь не найдена в графе документа")

    rel = dict(rels[match_idx])
    props = dict(rel.get("props") or {})
    props["expert_comment"] = body.expert_comment.strip()
    props["edited_by"] = editor
    props["edited_at"] = edited_at
    rel["props"] = props
    rels[match_idx] = rel

    expert_edits = list(payload.get("expert_edits") or [])
    expert_edits.append(
        {
            "from": from_,
            "to": to,
            "type": type,
            "expert_comment": props["expert_comment"],
            "edited_by": editor,
            "edited_at": edited_at,
        }
    )
    payload["relationships"] = rels
    payload["expert_edits"] = expert_edits[-200:]
    repo.save_graph(doc_id, payload)

    try:
        rel_type = type
        if re.match(r"^[A-Z_][A-Z0-9_]*$", rel_type):
            client = Neo4jClient.instance()
            cypher = f"""
            MATCH (a {{id: $from_id}})
            MATCH (b {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $props
            RETURN type(r) AS type
            """
            await client.run_write(
                cypher,
                {"from_id": from_, "to_id": to, "props": props},
            )
    except Exception as exc:
        log.warning("neo4j rel patch skipped doc_id=%s: %s", doc_id, exc)

    return GraphRelationshipPatchOut(
        document_id=doc_id,
        type=type,
        from_=from_,
        to=to,
        props=props,
        expert_edits_count=len(expert_edits),
    )


_ENTITY_LABELS = frozenset({
    "Material", "Process", "Equipment", "ChemicalReagent",
    "Organization", "Person", "Expert", "Facility",
})


def _canonical_entity_key(node: dict[str, Any]) -> str | None:
    label = str(node.get("label") or "")
    if label not in _ENTITY_LABELS:
        return None
    props = dict(node.get("props") or {})
    nid = str(node.get("id") or "")
    base = nid
    if ":" in nid:
        prefix, rest = nid.split(":", 1)
        if len(prefix) >= 8 or prefix.startswith("doc_"):
            base = rest
    name = props.get("name_en") or props.get("name_ru") or props.get("title_ru") or ""
    if name:
        slug = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9]+", "-", str(name).strip().lower())[:48].strip("-")
        return f"{label}:{slug}"
    return f"{label}:{base}"


def _annotate_multi_doc_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, set[str]] = {}
    for n in nodes:
        key = _canonical_entity_key(n)
        if not key:
            continue
        doc = str((n.get("props") or {}).get("source_doc_id") or "")
        if doc:
            by_key.setdefault(key, set()).add(doc)
    out: list[dict[str, Any]] = []
    for n in nodes:
        key = _canonical_entity_key(n)
        docs = by_key.get(key or "", set())
        if key and len(docs) >= 2:
            props = dict(n.get("props") or {})
            props["multi_doc_count"] = len(docs)
            props["multi_doc_ids"] = sorted(docs)
            out.append({**n, "props": props})
        else:
            out.append(n)
    return out


@app.get(f"{API}/graph/all", response_model=GraphOut)
async def get_merged_graph(request: Request) -> GraphOut:
    """Объединённый граф всех документов с узлами."""
    allowed = await _document_access(role_from_request(request))
    try:
        items, _ = await db_list_documents(1, 500, classifications=allowed)
    except Exception:
        items, _ = get_repo().list(1, 500, classifications=allowed)
    merged_nodes: list[dict] = []
    merged_rels: list[dict] = []
    seen_ids: set[str] = set()
    id_map: dict[str, str] = {}

    for rec in items:
        doc_id = rec["id"]
        if (rec.get("graph_nodes") or 0) == 0:
            continue
        payload = get_repo().read_graph(doc_id)
        if not payload or not payload.get("nodes"):
            continue
        for n in payload.get("nodes") or []:
            raw_id = str(n.get("id"))
            uid = raw_id if raw_id not in seen_ids else f"{doc_id}:{raw_id}"
            seen_ids.add(uid)
            id_map[f"{doc_id}:{raw_id}"] = uid
            if raw_id != uid:
                id_map[raw_id] = uid
            props = dict(n.get("props") or {})
            props["source_doc_id"] = doc_id
            props["source_file"] = rec.get("file_name") or doc_id
            merged_nodes.append({**n, "id": uid, "props": props})
        for r in payload.get("relationships") or []:
            fr = str(r.get("from") or r.get("from_") or "")
            to = str(r.get("to") or "")
            fr_u = id_map.get(f"{doc_id}:{fr}", id_map.get(fr, fr))
            to_u = id_map.get(f"{doc_id}:{to}", id_map.get(to, to))
            merged_rels.append({**r, "from": fr_u, "to": to_u})

    if not merged_nodes:
        raise HTTPException(status_code=404, detail="Нет документов с графом")
    cleaned = dedupe_graph_payload(
        GraphPayload(nodes=merged_nodes, relationships=merged_rels)
    ).as_dict()
    annotated_nodes = _annotate_multi_doc_nodes(cleaned.get("nodes", []))
    nodes = [GraphNode(**n) for n in annotated_nodes]
    relationships = [
        GraphRelationship(
            type=r.get("type", ""),
            from_=r.get("from", ""),
            to=r.get("to", ""),
            props=r.get("props", {}),
        )
        for r in cleaned.get("relationships", [])
    ]
    return GraphOut(document_id="__all__", nodes=nodes, relationships=relationships)


@app.get(f"{API}/documents/{{doc_id}}/pipeline/layers", response_model=LayerPipelineOut)
async def get_layer_pipeline(request: Request, doc_id: str) -> LayerPipelineOut:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    rec = _merge_repo(rec)
    graph = get_repo().read_graph(doc_id)
    md = get_repo().read_markdown(doc_id)
    payload = build_layer_pipeline(
        doc_status=rec.get("status"),
        step=rec.get("step"),
        graph=graph,
        md_ready=bool(md and md.strip()),
    )
    return LayerPipelineOut(**payload)


@app.get(f"{API}/pipeline/{{doc_id}}")
async def get_pipeline_trace(request: Request, doc_id: str) -> dict:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await assert_document_access(
        role_from_request(request),
        rec.get("classification"),
    )
    rec = _merge_repo(rec)
    nodes, rels, neo4j_synced = _graph_stats(doc_id, rec)
    return {
        "document_id": doc_id,
        "status": rec.get("status"),
        "step": rec.get("step"),
        "graph_nodes": nodes,
        "graph_relationships": rels,
        "neo4j_synced": neo4j_synced,
        "error": rec.get("error") or rec.get("neo4j_error"),
    }


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = STATIC_DIR / "index.html"
    body = html.read_text(encoding="utf-8") if html.exists() else "<h1>MKG Gateway</h1>"
    return HTMLResponse(content=body, headers={"Cache-Control": "no-store"})
