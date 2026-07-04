"""In-app documentation: markdown from Docs/ and static/docs/."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(tags=["documentation"])

_APP_DIR = Path(__file__).resolve().parent

DOC_SECTIONS: dict[str, dict[str, str]] = {
    "pipeline": {
        "title": "Пайплайн и слои L1–L6",
        "file": "21_pipeline_and_layers.md",
        "source": "repo",
    },
    "layer-agents": {
        "title": "Межслойные агенты (L1–L6)",
        "file": "24_layer_agents.md",
        "source": "repo",
    },
    "chat-agents": {
        "title": "Чат, роли и AI-агенты",
        "file": "22_chat_agents.md",
        "source": "repo",
    },
    "hrm-reasoning": {
        "title": "HRM: адаптивное число циклов",
        "file": "29_hrm_adaptive_reasoning.md",
        "source": "repo",
    },
    "analytics-synthesis": {
        "title": "Аналитика и синтез ответов",
        "file": "25_analytics_synthesis.md",
        "source": "repo",
    },
    "agent-hierarchy": {
        "title": "Иерархия агентов",
        "file": "23_agent_hierarchy.md",
        "source": "repo",
    },
    "orchestrator": {
        "title": "Оркестратор L1–L6",
        "file": "orchestrator.md",
        "source": "repo",
    },
    "key-requirements": {
        "title": "Ключевые требования хакатона",
        "file": "25_key_requirements.md",
        "source": "repo",
    },
    "functional-filters": {
        "title": "Функциональные фильтры",
        "file": "25_functional_filters.md",
        "source": "repo",
    },
    "roles-vs-agents": {
        "title": "Роли vs агенты",
        "file": "roles-vs-agents.md",
        "source": "repo",
    },
    "additional-wishes": {
        "title": "Дополнительные пожелания (MVP)",
        "file": "27_additional_wishes.md",
        "source": "repo",
    },
    "access-and-security": {
        "title": "Доступ и безопасность",
        "file": "28_access_and_security.md",
        "source": "repo",
    },
}


def _doc_roots(source: str) -> list[Path]:
    static_docs = _APP_DIR / "static" / "docs"
    if source == "static":
        return [static_docs]
    roots: list[Path] = [Path("/app/Docs"), static_docs]
    seen = {str(p) for p in roots}
    for parent in _APP_DIR.parents:
        candidate = parent / "Docs"
        key = str(candidate)
        if key not in seen:
            roots.append(candidate)
            seen.add(key)
    return roots


def _resolve_doc_path(slug: str) -> Path | None:
    meta = DOC_SECTIONS.get(slug)
    if not meta:
        return None
    fname = meta["file"]
    for root in _doc_roots(meta["source"]):
        candidate = root / fname
        if candidate.is_file():
            return candidate
    return None


class DocSectionOut(BaseModel):
    id: str
    title: str


class DocContentOut(BaseModel):
    id: str
    title: str
    content: str
    format: str = "markdown"


@router.get("/docs/sections", response_model=list[DocSectionOut])
async def list_doc_sections() -> list[DocSectionOut]:
    return [DocSectionOut(id=sid, title=meta["title"]) for sid, meta in DOC_SECTIONS.items()]


@router.get("/docs/{slug}", response_model=DocContentOut)
async def get_doc_content(slug: str) -> DocContentOut:
    meta = DOC_SECTIONS.get(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Раздел документации не найден")
    path = _resolve_doc_path(slug)
    if not path:
        raise HTTPException(status_code=404, detail=f"Файл {meta['file']} недоступен")
    return DocContentOut(
        id=slug,
        title=meta["title"],
        content=path.read_text(encoding="utf-8"),
    )


@router.get("/docs/{slug}/raw", response_class=PlainTextResponse)
async def get_doc_raw(slug: str) -> str:
    path = _resolve_doc_path(slug)
    if not path:
        raise HTTPException(status_code=404, detail="not found")
    return path.read_text(encoding="utf-8")
