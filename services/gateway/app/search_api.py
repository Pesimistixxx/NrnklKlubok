"""Unified search across all Qdrant collections (L3 chunks, L4 claims, L1 entities)."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from mkg_core.embeddings import ENTITY_LABELS, search_entities, search_global

from app.data_access import allowed_classifications
from app.request_context import role_from_request
from app.schemas import EntitySearchOut, UnifiedSearchOut, UnifiedSearchRequest

router = APIRouter(tags=["search"])


async def _run_unified_search(
    query: str,
    *,
    limit: int = 20,
    mode: str = "auto",
    layers: list[str] | None = None,
    document_ids: list[str] | None = None,
    allowed: list[str] | None = None,
) -> UnifiedSearchOut:
    result = await search_global(
        query,
        limit=limit,
        mode=mode,  # type: ignore[arg-type]
        layers=layers,
        document_ids=document_ids,
        allowed_classifications=allowed,
    )
    return UnifiedSearchOut(
        query=query,
        mode=result["mode"],
        hits=result.get("hits") or [],
        total=result.get("total") or len(result.get("hits") or []),
        collections=result.get("collections") or {},
        note=result.get("note"),
    )


@router.get(
    "/search",
    response_model=UnifiedSearchOut,
    summary="Поиск по всем слоям Qdrant (L1+L3+L4)",
)
async def get_unified_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=100),
    mode: str = Query("auto", description="auto | semantic"),
    layers: str | None = Query(None, description="Фильтр слоёв: L1,L3,L4"),
    document_id: str | None = Query(None, description="Ограничить одним документом"),
) -> UnifiedSearchOut:
    """GET-поиск по mkg_chunks + mkg_claims + mkg_entities параллельно, merge по score."""
    layer_list = [x.strip() for x in layers.split(",") if x.strip()] if layers else None
    doc_ids = [document_id] if document_id else None
    allowed = await allowed_classifications(role_from_request(request))
    return await _run_unified_search(
        q,
        limit=limit,
        mode=mode,
        layers=layer_list,
        document_ids=doc_ids,
        allowed=allowed,
    )


@router.post(
    "/search",
    response_model=UnifiedSearchOut,
    summary="Поиск по всем слоям Qdrant (POST)",
)
async def post_unified_search(body: UnifiedSearchRequest, request: Request) -> UnifiedSearchOut:
    """POST-поиск по всем коллекциям Qdrant с тегами слоя в каждом hit."""
    allowed = await allowed_classifications(role_from_request(request, body_role_id=body.role_id))
    return await _run_unified_search(
        body.query,
        limit=body.limit,
        mode=body.mode,
        layers=body.layers,
        document_ids=body.document_ids,
        allowed=allowed,
    )


@router.get(
    "/search/entities",
    response_model=EntitySearchOut,
    summary="Поиск материалов и процессов (mkg_entities)",
)
async def get_entity_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    types: str = Query(
        "Material,Process,Equipment,TechnologySolution",
        description="Типы сущностей через запятую",
    ),
    limit: int = Query(20, ge=1, le=100),
    document_id: str | None = Query(None, description="Ограничить одним документом"),
) -> EntitySearchOut:
    """Семантический поиск сущностей в коллекции mkg_entities (legacy endpoint)."""
    from mkg_core.config import get_settings

    type_list = [t.strip() for t in types.split(",") if t.strip()]
    entity_types = [t for t in type_list if t in ENTITY_LABELS]
    if not entity_types:
        entity_types = list(ENTITY_LABELS)
    doc_ids = [document_id] if document_id else None
    class_allowed = await allowed_classifications(role_from_request(request))
    from app.storage import get_repo

    hits = await search_entities(
        q,
        types=entity_types,
        limit=limit,
        document_id=document_id,
        document_ids=doc_ids,
    )
    hits = [
        h for h in hits
        if not h.get("document_id")
        or (get_repo().get(str(h.get("document_id"))) or {}).get("classification", "открытый") in class_allowed
    ]
    return EntitySearchOut(
        query=q,
        types=entity_types,
        hits=hits,
        total=len(hits),
        collection=get_settings().qdrant_collection_entities,
    )
