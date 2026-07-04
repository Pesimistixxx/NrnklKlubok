"""Проверка доступности всех внешних сервисов и API."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from mkg_core.config import get_settings


async def _check(name: str, fn) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        detail = await fn()
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"name": name, "ok": True, "latency_ms": ms, "detail": detail}
    except Exception as exc:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"name": name, "ok": False, "latency_ms": ms, "error": str(exc)}


async def check_postgres() -> str:
    from mkg_core.meta_db import pool

    p = await pool()
    async with p.acquire() as conn:
        val = await conn.fetchval("SELECT 1")
    return f"postgres ok ({val})"


async def check_redis() -> str:
    from mkg_core.queue import redis_settings
    from arq import create_pool

    pool = await create_pool(redis_settings())
    await pool.ping()
    await pool.close()
    return "redis pong"


async def check_neo4j() -> str:
    from mkg_core.neo4j_client import Neo4jClient

    client = Neo4jClient.instance()
    await client.verify()
    rows = await client.run("RETURN 1 AS n")
    return f"neo4j ok (n={rows[0]['n']})"


async def check_qdrant() -> str:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{settings.qdrant_url.rstrip('/')}/collections")
        resp.raise_for_status()
        cols = resp.json().get("result", {}).get("collections", [])
    return f"qdrant ok ({len(cols)} collections)"


def _require_yandex_llm() -> None:
    settings = get_settings()
    if not settings.yandex_api_key:
        raise RuntimeError("YANDEX_API_KEY не задан")
    if not settings.yandex_folder_id:
        raise RuntimeError("YANDEX_FOLDER_ID не задан")


def _require_yandex_ocr() -> None:
    settings = get_settings()
    if not settings.yandex_api_key:
        raise RuntimeError("YANDEX_API_KEY не задан")
    if not settings.yandex_folder_id:
        raise RuntimeError("YANDEX_FOLDER_ID не задан (x-folder-id)")
    settings.auth_headers_ocr_vision()


def _ocr_base_url() -> str:
    url = get_settings().yandex_ocr_url.rstrip("/")
    if url.endswith("/recognizeText"):
        return url[: -len("/recognizeText")]
    return "https://ocr.api.cloud.yandex.net/ocr/v1"


# 1×1 PNG — валидное тело для проверки auth (битый PDF давал HTTP 500).
_PROBE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


async def _probe_ocr_endpoint(
    client: httpx.AsyncClient,
    path: str,
    headers: dict[str, str],
    *,
    mime_type: str,
    content_b64: str,
    model: str = "page",
) -> None:
    resp = await client.post(
        f"{_ocr_base_url()}/{path}",
        headers=headers,
        json={
            "mimeType": mime_type,
            "languageCodes": ["ru"],
            "model": model,
            "content": content_b64,
        },
    )
    if resp.status_code in (401, 403):
        detail = resp.text[:200].strip() or resp.reason_phrase
        raise RuntimeError(
            f"{path}: {resp.status_code} — {detail}. "
            "Проверьте: scope yc.ai.vision.execute, роль ai.vision.user на каталоге."
        )
    # 200 — распознано; 400 — auth прошёл, тело не принято (для probe это OK)
    if resp.status_code in (200, 400):
        return
    detail = resp.text[:200].strip() or resp.reason_phrase
    raise RuntimeError(f"{path}: HTTP {resp.status_code} — {detail}")


async def check_yandex_llm() -> str:
    _require_yandex_llm()
    from mkg_core.llm import YandexLLMClient

    settings = get_settings()
    llm = YandexLLMClient.instance()
    text = await llm.generate("ping", "ping", max_output_tokens=8, temperature=0)
    return f"LLM ok · project={settings.yandex_folder_id} · {text!r}"


async def check_yandex_ocr() -> str:
    _require_yandex_ocr()
    settings = get_settings()
    headers = settings.auth_headers_ocr_vision()
    async with httpx.AsyncClient(timeout=30.0) as client:
        await _probe_ocr_endpoint(
            client,
            "recognizeText",
            headers,
            mime_type="PNG",
            content_b64=_PROBE_PNG_B64,
        )
    return "OCR ok · Api-Key + x-folder-id · recognizeText"


async def run_diagnostics() -> dict[str, Any]:
    settings = get_settings()
    checks = await asyncio.gather(
        _check("postgres", check_postgres),
        _check("redis", check_redis),
        _check("neo4j", check_neo4j),
        _check("qdrant", check_qdrant),
        _check("yandex_llm", check_yandex_llm),
        _check("yandex_ocr", check_yandex_ocr),
    )
    ok = all(c["ok"] for c in checks)
    return {
        "status": "ok" if ok else "degraded",
        "env": settings.app_env,
        "yandex_key_hint": (
            "LLM → OpenAI SDK (Bearer внутри SDK). "
            "OCR → Api-Key + x-folder-id (тот же YANDEX_API_KEY, другой формат заголовка). "
            "При 401: scope yc.ai.vision.execute + роль ai.vision.user на каталоге."
        ),
        "checks": checks,
    }
