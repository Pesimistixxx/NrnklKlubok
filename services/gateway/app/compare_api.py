"""API сравнительного анализа технологий."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from mkg_core.comparison import merge_repo_comparison, rows_to_csv, run_comparison_analysis

from app.storage import get_repo

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/technologies")
async def compare_technologies(
    q: str = Query("", description="Поисковый запрос / названия технологий"),
    limit: int = Query(10, ge=1, le=30),
    document_ids: str = Query("", description="CSV doc ids"),
    fill_llm: bool = Query(True, description="Дополнить пробелы через LLM"),
) -> dict[str, Any]:
    """Таблица сравнения Process/Material/TechnologySolution из графов документов."""
    doc_ids = [d.strip() for d in document_ids.split(",") if d.strip()] or None
    if fill_llm:
        result = await run_comparison_analysis(
            q,
            document_ids=doc_ids,
            use_llm=True,
            limit=limit,
        )
        return {
            "query": q,
            "rows": result["rows"],
            "partial": result["partial"],
            "gap_count": result["gap_count"],
            "llm_filled": result["llm_filled"],
            "markdown": result["markdown"],
        }

    rows, meta = merge_repo_comparison(get_repo(), document_ids=doc_ids, query=q, limit=limit)
    return {
        "query": q,
        "rows": rows,
        "partial": meta.get("partial", False),
        "gap_count": meta.get("gap_count", 0),
        "llm_filled": False,
    }


@router.get("/technologies.csv")
async def compare_technologies_csv(
    q: str = Query(""),
    limit: int = Query(30, ge=1, le=50),
    document_ids: str = Query(""),
) -> dict[str, str]:
    doc_ids = [d.strip() for d in document_ids.split(",") if d.strip()] or None
    rows, _meta = merge_repo_comparison(get_repo(), document_ids=doc_ids, query=q, limit=limit)
    return {"filename": "mkg-tech-comparison.csv", "content": rows_to_csv(rows)}
