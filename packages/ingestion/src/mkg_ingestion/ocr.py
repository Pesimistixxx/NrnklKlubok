"""Yandex Vision OCR + локальный fallback для PDF.

Аутентификация OCR:
  Authorization: Api-Key <YANDEX_API_KEY>
  x-folder-id: <YANDEX_FOLDER_ID>
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx

from mkg_core import get_settings
from mkg_core.api_errors import is_fatal_api_error

try:
    from mkg_core.pipeline_log import log_event
except ImportError:  # pragma: no cover
    def log_event(*args, **kwargs):  # type: ignore[misc]
        pass

try:
    import fitz  # pymupdf
except Exception:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

_OCR_BASE = "https://ocr.api.cloud.yandex.net/ocr/v1"
_POLL_INTERVAL_S = 5.0
_MAX_POLL_ATTEMPTS = 120
_OCR_RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}

_EXT_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


def _ocr_base_url() -> str:
    url = get_settings().yandex_ocr_url.rstrip("/")
    if url.endswith("/recognizeText"):
        return url[: -len("/recognizeText")]
    return _OCR_BASE


def _ocr_auth_headers() -> dict[str, str]:
    return get_settings().auth_headers_ocr_vision()


def _mime_for(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    mime = _EXT_MIME.get(ext)
    if mime and mime.startswith("image/"):
        # Yandex принимает общий тип "image" для растровых форматов.
        return "image"
    return mime or "application/octet-stream"


def pdf_page_count(content: bytes) -> int:
    if fitz is not None:
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                return doc.page_count
        except Exception:
            pass
    m = re.search(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", content[:65536])
    if m:
        return max(int(m.group(1)), 1)
    return 1


def extract_pdf_local(content: bytes) -> str:
    """Локальное извлечение текста из PDF (fallback без OCR)."""
    if fitz is None:
        return ""
    parts: list[str] = []
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text = page.get_text("text").strip()
                if text:
                    parts.append(text)
    except Exception:
        return ""
    return "\n\n".join(parts)


def _build_body(content: bytes, mime_type: str, *, model: str) -> dict[str, Any]:
    return {
        "mimeType": mime_type,
        "languageCodes": ["ru", "en"],
        "model": model,
        "content": base64.b64encode(content).decode("ascii"),
    }


def _annotation_from(obj: Any) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    ta = obj.get("textAnnotation")
    if isinstance(ta, dict):
        return ta
    result = obj.get("result")
    if isinstance(result, dict):
        ta2 = result.get("textAnnotation")
        if isinstance(ta2, dict):
            return ta2
    return None


def _text_from_annotation(annotation: dict[str, Any], container: dict[str, Any]) -> str:
    for key in ("markdown", "fullText"):
        val = annotation.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    result = container.get("result")
    if isinstance(result, dict):
        for key in ("markdown", "text", "fullText"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    lines: list[str] = []
    blocks = annotation.get("blocks") or []
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            for line in block.get("lines") or []:
                if not isinstance(line, dict):
                    continue
                line_text = line.get("text")
                if not line_text:
                    words = [
                        w.get("text", "")
                        for w in (line.get("words") or [])
                        if isinstance(w, dict)
                    ]
                    line_text = " ".join(w for w in words if w)
                if isinstance(line_text, str) and line_text.strip():
                    lines.append(line_text.strip())
    return "\n".join(lines)


def _text_from_payload(data: Any) -> str:
    if isinstance(data, str):
        chunks = _split_concatenated_json(data)
        if chunks:
            return _text_from_payload(chunks)
        return data.strip()
    if isinstance(data, list):
        parts: list[str] = []
        for item in data:
            t = _text_from_payload(item)
            if t:
                parts.append(t)
        return "\n\n".join(parts)
    if not isinstance(data, dict):
        return ""
    if data.get("error"):
        return ""
    if data.get("done") is False:
        return ""
    inner = data.get("response")
    if inner is not None and inner is not data:
        t = _text_from_payload(inner)
        if t:
            return t
    annotation = _annotation_from(data)
    if annotation:
        return _text_from_annotation(annotation, data)
    for key in ("markdown", "text", "fullText"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    result = data.get("result")
    if isinstance(result, dict):
        for key in ("markdown", "text", "fullText"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def _split_concatenated_json(text: str) -> list[Any]:
    objects: list[Any] = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    objects.append(json.loads(text[start : i + 1]))
                except json.JSONDecodeError:
                    pass
                start = -1
    return objects


def _parse_ndjson(text: str) -> list[Any] | None:
    items: list[Any] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            return None
    return items if items else None


def _load_ocr_json(resp: httpx.Response) -> Any:
    """Разбор ответа OCR: один JSON, NDJSON (getRecognition) или склеенные объекты."""
    text = resp.text.strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    ndjson = _parse_ndjson(text)
    if ndjson is not None:
        return ndjson

    chunks = _split_concatenated_json(text)
    if chunks:
        return chunks if len(chunks) > 1 else chunks[0]

    return text


def _retry_after_seconds(resp: httpx.Response | None, fallback: float) -> float:
    if resp is not None:
        raw = resp.headers.get("retry-after")
        if raw:
            try:
                return max(float(raw), fallback)
            except ValueError:
                pass
    return fallback


def _http_status(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def _is_rate_limited_or_transient(exc: BaseException) -> bool:
    status = _http_status(exc)
    if status in _OCR_RETRY_STATUS:
        return True
    msg = str(exc).lower()
    return "too many requests" in msg or "429" in msg or "timeout" in msg


async def _ocr_sync(client: httpx.AsyncClient, content: bytes, mime_type: str, *, model: str) -> str:
    url = f"{_ocr_base_url()}/recognizeText"
    req = {"url": url, "mime_type": mime_type, "model": model, "bytes": len(content)}
    delay = 8.0
    last_exc: Exception | None = None
    for attempt in range(1, 6):
        try:
            resp = await client.post(url, headers=_ocr_auth_headers(), json=_build_body(content, mime_type, model=model))
            if resp.status_code in _OCR_RETRY_STATUS:
                wait = _retry_after_seconds(resp, delay)
                log_event("ocr_sync_retry", request=req | {"attempt": attempt}, error=f"HTTP {resp.status_code}; sleep {wait:.1f}s")
                await asyncio.sleep(wait)
                delay = min(delay * 1.8, 90.0)
                continue
            resp.raise_for_status()
            text = _text_from_payload(_load_ocr_json(resp))
            log_event("ocr_sync", request=req, response={"chars": len(text), "preview": text[:500]})
            return text
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code not in _OCR_RETRY_STATUS:
                log_event("ocr_sync", request=req, error=str(exc))
                raise
            wait = _retry_after_seconds(exc.response, delay)
            log_event("ocr_sync_retry", request=req | {"attempt": attempt}, error=f"{exc}; sleep {wait:.1f}s")
            await asyncio.sleep(wait)
            delay = min(delay * 1.8, 90.0)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            log_event("ocr_sync_retry", request=req | {"attempt": attempt}, error=f"{exc}; sleep {delay:.1f}s")
            await asyncio.sleep(delay)
            delay = min(delay * 1.8, 90.0)
    err = last_exc or TimeoutError("OCR sync retry limit exceeded")
    log_event("ocr_sync", request=req, error=str(err))
    raise err


async def _ocr_async(client: httpx.AsyncClient, content: bytes, mime_type: str, *, model: str) -> str:
    base = _ocr_base_url()
    req = {"mime_type": mime_type, "model": model, "bytes": len(content)}
    submit_url = f"{base}/recognizeTextAsync"
    delay = 10.0
    submit: httpx.Response | None = None
    for attempt in range(1, 6):
        submit = await client.post(
            submit_url,
            headers=_ocr_auth_headers(),
            json=_build_body(content, mime_type, model=model),
        )
        if submit.status_code in _OCR_RETRY_STATUS:
            wait = _retry_after_seconds(submit, delay)
            log_event("ocr_async_submit_retry", request=req | {"attempt": attempt}, error=f"HTTP {submit.status_code}; sleep {wait:.1f}s")
            await asyncio.sleep(wait)
            delay = min(delay * 1.8, 120.0)
            continue
        submit.raise_for_status()
        break
    if submit is None:
        raise RuntimeError("recognizeTextAsync не вернул ответ")
    submit.raise_for_status()
    payload = submit.json()
    operation_id = payload.get("id") or payload.get("operationId")
    if not operation_id:
        raise RuntimeError("recognizeTextAsync не вернул operation id")
    req["operation_id"] = operation_id

    poll_url = f"{base}/getRecognition"
    not_found_count = 0
    for attempt in range(_MAX_POLL_ATTEMPTS):
        resp = await client.get(
            poll_url,
            headers=_ocr_auth_headers(),
            params={"operationId": operation_id},
        )
        if resp.status_code in (404, 425, 429):
            if resp.status_code == 404:
                not_found_count += 1
            wait = _retry_after_seconds(resp, min(_POLL_INTERVAL_S + attempt * 0.5, 30.0))
            log_event(
                "ocr_async_poll_wait",
                request=req | {"attempt": attempt + 1, "status": resp.status_code},
                error=f"operation not ready; sleep {wait:.1f}s",
            )
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        text = _text_from_payload(_load_ocr_json(resp))
        if text.strip():
            log_event("ocr_async", request=req, response={"chars": len(text), "preview": text[:500]})
            return text
        await asyncio.sleep(min(_POLL_INTERVAL_S + attempt * 0.5, 30.0))
    err = f"OCR timeout для operation {operation_id}; 404 polls={not_found_count}"
    log_event("ocr_async", request=req, error=err)
    raise TimeoutError(err)


def detect_ocr_model(file_name: str, content: bytes) -> tuple[str, str]:
    """Автовыбор режима Yandex Vision OCR по типу файла и структуре текста."""
    ext = Path(file_name).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}:
        return "page", "изображение → постраничный текст"

    sample = ""
    pages = 1
    if ext == ".pdf":
        pages = pdf_page_count(content)
        sample = extract_pdf_local(content)[:12000]
    else:
        sample = content[:12000].decode("utf-8", errors="ignore")

    if not sample.strip() and ext == ".pdf":
        return "markdown", "PDF без текста → markdown OCR"

    pipe_lines = sum(1 for line in sample.splitlines() if line.count("|") >= 2)
    if pipe_lines >= 5 or sample.count("|") > 50:
        return "table", "много таблиц/колонок с |"

    slide_pages = sum(1 for line in sample.splitlines() if re.match(r"^\|\s*\d+\s*\|", line.strip()))
    bullets = sample.count("•") + sample.count("\uf0b7") + sample.count("◼") + sample.count("")
    short_lines = sum(1 for line in sample.splitlines() if 0 < len(line.strip()) < 48)
    if slide_pages >= 2 or (bullets >= 6 and short_lines > 20):
        return "page-column-sort", "презентация/слайды с колонками"

    if pages == 1 and len(sample) < 2500:
        return "page", "короткий одностраничный документ"

    return "markdown", "отчёт/PDF → структурированный Markdown"


def _ocr_quality() -> str:
    return (get_settings().ocr_quality or "high").strip().lower()


def _render_pdf_page_png(page: Any, *, zoom: float = 2.0) -> bytes:
    """Рендер страницы PDF в PNG для OCR (выше разрешение → лучше качество)."""
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


async def _ocr_pdf_pages(
    client: httpx.AsyncClient,
    content: bytes,
    *,
    model: str,
    zoom: float = 2.0,
) -> str:
    """Постраничный OCR PDF через рендер в PNG + sync recognizeText."""
    if fitz is None:
        return await _ocr_async(client, content, "application/pdf", model=model)

    parts: list[str] = []
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page_idx, page in enumerate(doc):
                img = _render_pdf_page_png(page, zoom=zoom)
                page_text = await _ocr_sync(client, img, "image", model=model)
                if page_text.strip():
                    parts.append(page_text.strip())
                # Yandex OCR легко уходит в 429 при постраничном распознавании больших PDF.
                if page_idx < doc.page_count - 1:
                    await asyncio.sleep(3.0)
    except Exception as exc:
        log_event("ocr_pdf_pages", error=str(exc))
        return await _ocr_async(client, content, "application/pdf", model=model)

    if not parts:
        return await _ocr_async(client, content, "application/pdf", model=model)
    return "\n\n".join(parts)


def _needs_page_ocr(file_name: str, content: bytes) -> bool:
    """Скан/PDF без текстового слоя — лучше постраничный OCR."""
    ext = Path(file_name).suffix.lower()
    if ext != ".pdf":
        return False
    sample = extract_pdf_local(content)[:8000]
    if not sample.strip():
        return True
    # Мало текста на страницу — вероятно скан со встроенным шумом
    pages = max(pdf_page_count(content), 1)
    return len(sample.strip()) / pages < 120


async def ocr_file(file_name: str, content: bytes) -> str:
    """Извлечь текст/Markdown из PDF или изображения."""
    from mkg_core.runtime_config import get_ocr_model

    ext = Path(file_name).suffix.lower()
    mime = _mime_for(file_name)
    configured = await get_ocr_model()
    if configured and configured != "auto":
        ocr_model = configured
        ocr_reason = f"настройки → {configured}"
    else:
        ocr_model, ocr_reason = detect_ocr_model(file_name, content)
    quality = _ocr_quality()
    if quality == "high" and Path(file_name).suffix.lower() == ".pdf":
        if _needs_page_ocr(file_name, content) and ocr_model not in ("table", "handwritten"):
            ocr_model = "markdown"
            ocr_reason = f"{ocr_reason} · high → markdown постранично"
    settings = get_settings()
    log_event(
        "ocr_start",
        request={
            "file_name": file_name,
            "model": ocr_model,
            "auto_reason": ocr_reason,
            "mime": mime,
            "bytes": len(content),
            "auth": "Api-Key + x-folder-id",
            "quality": quality,
        },
    )

    try:
        settings.auth_headers_ocr_vision()
    except Exception as exc:
        local = extract_pdf_local(content) if ext == ".pdf" else ""
        if local.strip():
            return local
        raise RuntimeError(f"OCR недоступен: {exc}") from exc

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            if ext == ".pdf":
                pages = pdf_page_count(content)
                use_page_ocr = quality == "high" and (pages > 1 or _needs_page_ocr(file_name, content))
                if use_page_ocr:
                    text = await _ocr_pdf_pages(client, content, model=ocr_model)
                elif pages > 1:
                    text = await _ocr_async(client, content, "application/pdf", model=ocr_model)
                else:
                    text = await _ocr_sync(client, content, mime, model=ocr_model)
            else:
                text = await _ocr_sync(client, content, mime, model=ocr_model)
            if text.strip():
                return text
        except Exception as exc:
            if is_fatal_api_error(exc):
                if ext == ".pdf":
                    local = extract_pdf_local(content)
                    if local.strip():
                        log_event(
                            "ocr_fallback_local",
                            request={"reason": str(exc), "model": ocr_model},
                            response={"chars": len(local), "preview": local[:500]},
                        )
                        return local
                raise RuntimeError(f"OCR остановлен ({ocr_model}): {exc}") from exc
            if ext == ".pdf" and _is_rate_limited_or_transient(exc):
                local = extract_pdf_local(content)
                if local.strip():
                    log_event(
                        "ocr_fallback_local",
                        request={"reason": str(exc), "model": ocr_model, "fallback": "rate_limit_or_timeout"},
                        response={"chars": len(local), "preview": local[:500]},
                    )
                    return local
            if ext == ".pdf":
                try:
                    text = await _ocr_async(client, content, "application/pdf", model=ocr_model)
                    if text.strip():
                        return text
                except Exception as exc2:
                    if is_fatal_api_error(exc2):
                        local = extract_pdf_local(content)
                        if local.strip():
                            log_event(
                                "ocr_fallback_local",
                                request={"reason": str(exc2), "model": ocr_model},
                                response={"chars": len(local), "preview": local[:500]},
                            )
                            return local
                        raise RuntimeError(f"OCR остановлен ({ocr_model}): {exc2}") from exc2
                    if _is_rate_limited_or_transient(exc2):
                        local = extract_pdf_local(content)
                        if local.strip():
                            log_event(
                                "ocr_fallback_local",
                                request={"reason": str(exc2), "model": ocr_model, "fallback": "rate_limit_or_timeout"},
                                response={"chars": len(local), "preview": local[:500]},
                            )
                            return local
                    raise RuntimeError(f"OCR не удался ({ocr_model}): {exc2}") from exc2
            raise RuntimeError(f"OCR не удался ({ocr_model}): {exc}") from exc

    if ext == ".pdf":
        local = extract_pdf_local(content)
        if local.strip():
            return local

    raise RuntimeError(f"OCR вернул пустой текст (модель {ocr_model})")
