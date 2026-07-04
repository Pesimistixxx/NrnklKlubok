"""Конвейер обработки файла (ingestion).

Шаги: извлечение по формату → ремонт кодировки → чанкинг → очистка → markdown.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path

from mkg_core import YandexLLMClient, get_settings
from mkg_core.api_errors import format_api_error, is_fatal_api_error
from mkg_core.runtime_config import get_llm_model

from mkg_ingestion.formats import detect_route
from mkg_ingestion.parsers import extract_from_bytes

try:
    from mkg_prompts import PromptRegistry
except Exception:  # pragma: no cover
    PromptRegistry = None  # type: ignore[misc,assignment]

try:
    import ftfy
except Exception:  # pragma: no cover
    ftfy = None

try:
    from langdetect import detect as _detect_lang
except Exception:  # pragma: no cover
    _detect_lang = None


@dataclass
class Chunk:
    index: int
    text: str
    kind: str = "paragraph"
    lang: str | None = None
    useful: bool = True


@dataclass
class IngestResult:
    doc_id: str
    doc_type: str | None = None
    lang: str | None = None
    markdown: str = ""
    chunks: list[Chunk] = field(default_factory=list)


def detect_type(file_name: str) -> str:
    return detect_route(file_name)


async def extract_raw(file_name: str, content: bytes) -> str:
    return await extract_from_bytes(file_name, content)


def repair_encoding(text: str) -> str:
    if ftfy is not None:
        text = ftfy.fix_text(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_markdown(text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        kind = "heading" if block.startswith("#") else "paragraph"
        if block.startswith("|") and "|" in block:
            kind = "table"
        chunks.append(Chunk(index=idx, text=block, kind=kind))
        idx += 1
    return chunks


CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")
_PDF_MARKERS = ("%PDF-", "endobj", "endstream", "FlateDecode")


def is_junk(chunk: Chunk) -> bool:
    t = chunk.text
    if t.lstrip().startswith("%PDF-"):
        return True
    if sum(marker in t for marker in _PDF_MARKERS) >= 2:
        return True
    if len(t) < 3:
        return True
    cjk = len(CJK_RE.findall(t))
    if cjk and cjk / max(len(t), 1) > 0.3:
        return True
    letters = sum(ch.isalnum() for ch in t)
    if letters / max(len(t), 1) < 0.3:
        return True
    return False


def detect_lang(text: str) -> str | None:
    if _detect_lang is None:
        return None
    try:
        return _detect_lang(text)
    except Exception:
        return None


def assemble_markdown(title: str, chunks: list[Chunk]) -> str:
    body = "\n\n".join(c.text for c in chunks if c.useful)
    base = Path(title).stem
    if body.lstrip().startswith("#"):
        return body + "\n"
    return f"# {base}\n\n{body}\n"


async def process(doc_id: str, file_name: str, content: bytes) -> IngestResult:
    doc_type = detect_type(file_name)
    raw = await extract_raw(file_name, content)
    if not raw.strip():
        raise ValueError("Не удалось извлечь текст из файла")
    raw = repair_encoding(raw)
    chunks = chunk_markdown(raw)
    for c in chunks:
        c.useful = not is_junk(c)
        c.lang = detect_lang(c.text)
    await _apply_llm_chunk_filter(chunks)
    useful = [c for c in chunks if c.useful]
    if not useful:
        raise ValueError("После очистки не осталось полезного текста")
    doc_lang = detect_lang(raw)
    md = assemble_markdown(file_name, chunks)
    return IngestResult(
        doc_id=doc_id, doc_type=doc_type, lang=doc_lang, markdown=md, chunks=chunks
    )


async def _apply_llm_chunk_filter(chunks: list[Chunk]) -> None:
    if PromptRegistry is None:
        return
    settings = get_settings()
    if not settings.yandex_api_key:
        return
    model = await get_llm_model()
    try:
        PromptRegistry.configure(settings.prompts_path, model=model)
        reg = PromptRegistry.instance()
        llm = YandexLLMClient.instance()
    except Exception as exc:
        if is_fatal_api_error(exc):
            raise RuntimeError(format_api_error(exc, model=model)) from exc
        return

    concurrency = max(1, get_settings().llm_concurrency)
    sem = asyncio.Semaphore(concurrency)
    targets = [
        c for c in chunks
        if c.useful and c.kind != "heading" and len(c.text.strip()) >= 20
    ]

    async def _filter_chunk(c: Chunk) -> None:
        text = c.text.strip()
        try:
            prompt = reg.get(stage="ingestion", prompt_type="chunk_filter", text=text[:3000])
            async with sem:
                raw = await llm.chat(**prompt)
        except Exception as exc:
            # Фатальные ошибки (auth/квота) должны остановить пайплайн, остальные —
            # мягкая деградация: чанк остаётся полезным, эвристика уже отработала.
            if is_fatal_api_error(exc):
                raise RuntimeError(format_api_error(exc, model=model)) from exc
            return
        # Модель отвечает одним словом: useful | junk. Приоритет за useful,
        # чтобы ответы вида "not junk" не выбрасывали полезный текст.
        verdict = raw.strip().lower()
        if "useful" not in verdict and "junk" in verdict:
            c.useful = False

    if targets:
        results = await asyncio.gather(
            *[_filter_chunk(c) for c in targets], return_exceptions=True
        )
        for res in results:
            if isinstance(res, BaseException):
                raise res
