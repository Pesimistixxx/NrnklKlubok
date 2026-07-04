"""MKG Gateway — FastAPI: загрузка, UI, диагностика, конфиг моделей."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
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
from mkg_core.queue import enqueue, abort_job
from mkg_core.layer_pipeline import build_layer_pipeline
from mkg_core.llm_cache import LLMResponseCache
from mkg_ingestion.formats import formats_public, is_binary
from mkg_ingestion import process as run_ingestion_process
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.ontology import NODE_PROP_HINTS

from app.agent_api import router as agent_router
from app.agents_proxy import router as agents_proxy_router
from app.collab_api import router as collab_router
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
    LayerPipelineOut,
    PipelineLogOut,
    ClearDatabaseOut,
    RuntimeConfigOut,
    RuntimeConfigUpdate,
)
from app.storage import get_repo
from app.upload import accept_upload

log = setup_logging("gateway")
STATIC_DIR = Path(__file__).parent / "static"
API = "/api/v1"

app = FastAPI(
    title="MKG Gateway",
    version="0.4.0",
    description=(
        "Gateway MKG: загрузка документов, extraction, граф L1–L6. "
        "Agent API: `/api/v1/agents/` — см. Docs/14_agent_api.md"
    ),
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(agent_router, prefix=API)
app.include_router(collab_router, prefix=API)
app.include_router(agents_proxy_router, prefix=API)

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


def _to_out(rec: dict) -> DocumentOut:
    rec = _merge_repo(rec)
    upload_date = rec.get("upload_date")
    if upload_date is None:
        upload_date = "1970-01-01T00:00:00+00:00"
    return DocumentOut(
        id=rec["id"],
        file_name=rec["file_name"],
        doc_type=rec.get("doc_type"),
        mime_type=rec.get("mime_type"),
        classification=rec.get("classification", "открытый"),
        organization=rec.get("organization"),
        hash_sum=rec["hash_sum"],
        status=DocStatus(rec.get("status", "uploaded")),
        upload_date=upload_date,
        size_bytes=rec["size_bytes"],
        step=rec.get("step"),
        error=rec.get("error") or rec.get("neo4j_error"),
        neo4j_synced=rec.get("neo4j_synced"),
        graph_nodes=rec.get("graph_nodes"),
        graph_relationships=rec.get("graph_relationships"),
    )


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
    except Exception as exc:
        log.exception("inline ingestion failed doc_id=%s", doc_id)
        repo.set_status(doc_id, DocStatus.failed.value, error=str(exc))
        try:
            await update_document_status(doc_id, DocStatus.failed.value, error=str(exc))
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
async def get_node_field_hints() -> dict[str, list[str]]:
    """Ожидаемые props по метке узла — для UI и проверки extraction."""
    return {label: list(fields) for label, fields in NODE_PROP_HINTS.items()}


@app.post(f"{API}/documents", response_model=DocumentOut)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    classification: str = Form("открытый"),
) -> DocumentOut:
    content = await file.read()
    try:
        rec = await accept_upload(file.filename or "unnamed", content, classification=classification)
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
) -> BatchUploadOut:
    if not files:
        raise HTTPException(status_code=400, detail="Не переданы файлы")
    items: list[BatchUploadItem] = []
    uploaded = failed = 0
    for file in files:
        name = file.filename or "unnamed"
        content = await file.read()
        try:
            rec = await accept_upload(name, content, classification=classification)
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
    if not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    get_repo().set_status(doc_id, DocStatus.uploaded.value, error=None, step="reprocess")
    job_id = await enqueue("run_ingestion", doc_id)
    if job_id is None:
        background.add_task(_run_ingestion_inline, doc_id)
    return {"document_id": doc_id, "status": DocStatus.processing.value}


@app.get(f"{API}/documents", response_model=DocumentList)
async def list_documents(page: int = 1, page_size: int = 20) -> DocumentList:
    try:
        items, total = await db_list_documents(page, page_size)
    except Exception:
        items, total = get_repo().list(page, page_size)
    return DocumentList(
        items=[_to_out(r) for r in items], total=total, page=page, page_size=page_size
    )


@app.get(f"{API}/documents/{{doc_id}}", response_model=DocumentOut)
async def get_document(doc_id: str) -> DocumentOut:
    rec = None
    try:
        rec = await db_get_document(doc_id)
    except Exception:
        rec = None
    if not rec:
        rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return _to_out(rec)


@app.get(f"{API}/documents/{{doc_id}}/markdown", response_class=PlainTextResponse)
async def get_markdown(doc_id: str) -> str:
    md = get_repo().read_markdown(doc_id)
    if md is None:
        raise HTTPException(status_code=404, detail="Markdown ещё не готов")
    return md


@app.get(f"{API}/documents/{{doc_id}}/source")
async def get_source(doc_id: str) -> Response:
    raw = get_repo().read_source(doc_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Исходник не найден")
    rec = get_repo().get(doc_id) or {}
    return Response(content=raw, media_type=rec.get("mime_type") or "application/octet-stream")


@app.post(f"{API}/documents/{{doc_id}}/submit")
async def submit_document(doc_id: str) -> dict[str, str]:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if rec.get("status") not in (DocStatus.md_ready.value, DocStatus.loaded.value, DocStatus.failed.value):
        raise HTTPException(status_code=409, detail="Дождитесь md_ready")
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
async def get_preview(doc_id: str) -> dict:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
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
        "lang": rec.get("lang"),
        "step": rec.get("step"),
        "source_kind": source_kind,
        "source_text": source_text,
        "markdown": clean_md,
        "markdown_marked": build_marked_markdown(doc_id, clean_md, get_repo().read_graph(doc_id)),
        "error": rec.get("error") or rec.get("neo4j_error"),
        "graph_nodes": nodes,
        "graph_relationships": rels,
        "neo4j_synced": neo4j_synced,
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


@app.get(f"{API}/documents/{{doc_id}}/logs", response_model=PipelineLogOut)
async def get_document_logs(doc_id: str, limit: int = 100) -> PipelineLogOut:
    if not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    return PipelineLogOut(document_id=doc_id, items=read_logs(doc_id, limit=limit))


@app.get(f"{API}/graph/documents/{{doc_id}}", response_model=GraphOut)
async def get_document_graph(doc_id: str) -> GraphOut:
    if not get_repo().get(doc_id):
        raise HTTPException(status_code=404, detail="Документ не найден")
    payload = get_repo().read_graph(doc_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Граф ещё не сформирован")
    cleaned = dedupe_graph_payload(
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


@app.get(f"{API}/graph/all", response_model=GraphOut)
async def get_merged_graph() -> GraphOut:
    """Объединённый граф всех документов с узлами."""
    items, _ = await db_list_documents(1, 500)
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
    return GraphOut(document_id="__all__", nodes=nodes, relationships=relationships)


@app.get(f"{API}/documents/{{doc_id}}/pipeline/layers", response_model=LayerPipelineOut)
async def get_layer_pipeline(doc_id: str) -> LayerPipelineOut:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
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
async def get_pipeline_trace(doc_id: str) -> dict:
    rec = get_repo().get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Документ не найден")
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
