"""Runtime-конфиг моделей (LLM, OCR) в Postgres с in-memory кэшем."""
from __future__ import annotations

from typing import Any

from mkg_core.config import get_settings

_CACHE: dict[str, str] = {}
_LOADED = False

LLM_MODELS = ("yandexgpt-5.1", "yandexgpt-5-lite", "yandexgpt", "aliceai-llm")
OCR_MODELS = ("auto", "markdown", "page", "page-column-sort", "table", "handwritten")
EMB_DOC_MODELS = (
    "text-search-doc/latest",
    "text-search-doc",
    "text-search-doc/rc",
)
EMB_QUERY_MODELS = (
    "text-search-query/latest",
    "text-search-query",
    "text-search-query/rc",
)
OCR_MODEL_LABELS: dict[str, str] = {
    "auto": "auto — автоматически по типу файла (рекомендуется)",
    "markdown": "markdown — PDF/сканы → структурированный Markdown",
    "page": "page — обычный печатный текст, одна колонка",
    "page-column-sort": "page-column-sort — многоколоночные документы",
    "table": "table — страницы с таблицами",
    "handwritten": "handwritten — рукописный текст (ru/en)",
}
EMB_MODEL_LABELS: dict[str, str] = {
    "text-search-doc/latest": "text-search-doc/latest — индексация документов",
    "text-search-doc": "text-search-doc — базовая doc-модель",
    "text-search-doc/rc": "text-search-doc/rc — release candidate",
    "text-search-query/latest": "text-search-query/latest — семантический поиск",
    "text-search-query": "text-search-query — базовая query-модель",
    "text-search-query/rc": "text-search-query/rc — release candidate",
}
DEFAULTS = {
    "llm_model": "yandexgpt-5.1",
    "ocr_model": "auto",
    "emb_doc_model": "text-search-doc/latest",
    "emb_query_model": "text-search-query/latest",
}


async def init_runtime_schema() -> None:
    from mkg_core.meta_db import pool

    sql = """
    CREATE TABLE IF NOT EXISTS runtime_config (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(sql)
        for key, val in DEFAULTS.items():
            await conn.execute(
                """
                INSERT INTO runtime_config (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO NOTHING
                """,
                key,
                val,
            )


async def load_runtime_config() -> dict[str, str]:
    global _LOADED
    settings = get_settings()
    _CACHE.setdefault("llm_model", settings.yandex_model_pro or DEFAULTS["llm_model"])
    _CACHE.setdefault("ocr_model", DEFAULTS["ocr_model"])
    _CACHE.setdefault("emb_doc_model", settings.yandex_emb_doc or DEFAULTS["emb_doc_model"])
    _CACHE.setdefault("emb_query_model", settings.yandex_emb_query or DEFAULTS["emb_query_model"])
    try:
        await init_runtime_schema()
        from mkg_core.meta_db import pool

        p = await pool()
        async with p.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM runtime_config")
        for row in rows:
            _CACHE[str(row["key"])] = str(row["value"])
        _LOADED = True
    except Exception:
        _LOADED = True
    return dict(_CACHE)


async def get_config(key: str) -> str:
    if not _LOADED:
        await load_runtime_config()
    return _CACHE.get(key, DEFAULTS.get(key, ""))


async def get_llm_model() -> str:
    return await get_config("llm_model")


async def get_ocr_model() -> str:
    return await get_config("ocr_model")


async def get_emb_doc_model() -> str:
    return await get_config("emb_doc_model")


async def get_emb_query_model() -> str:
    return await get_config("emb_query_model")


async def set_config(values: dict[str, str]) -> dict[str, str]:
    await init_runtime_schema()
    from mkg_core.meta_db import pool

    allowed = {"llm_model", "ocr_model", "emb_doc_model", "emb_query_model"}
    p = await pool()
    async with p.acquire() as conn:
        for key, value in values.items():
            if key not in allowed:
                continue
            if key == "llm_model" and value not in LLM_MODELS:
                raise ValueError(f"Неизвестная LLM-модель: {value}")
            if key == "ocr_model" and value not in OCR_MODELS:
                raise ValueError(f"Неизвестная OCR-модель: {value}")
            if key == "emb_doc_model" and value not in EMB_DOC_MODELS:
                raise ValueError(f"Неизвестная embedding doc-модель: {value}")
            if key == "emb_query_model" and value not in EMB_QUERY_MODELS:
                raise ValueError(f"Неизвестная embedding query-модель: {value}")
            await conn.execute(
                """
                INSERT INTO runtime_config (key, value, updated_at)
                VALUES ($1, $2, now())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                """,
                key,
                value,
            )
            _CACHE[key] = value
    return dict(_CACHE)


async def public_config() -> dict[str, Any]:
    cfg = await load_runtime_config()
    return {
        "llm_model": cfg.get("llm_model", DEFAULTS["llm_model"]),
        "ocr_model": cfg.get("ocr_model", DEFAULTS["ocr_model"]),
        "emb_doc_model": cfg.get("emb_doc_model", DEFAULTS["emb_doc_model"]),
        "emb_query_model": cfg.get("emb_query_model", DEFAULTS["emb_query_model"]),
        "llm_models": list(LLM_MODELS),
        "ocr_models": list(OCR_MODELS),
        "emb_doc_models": list(EMB_DOC_MODELS),
        "emb_query_models": list(EMB_QUERY_MODELS),
        "ocr_model_labels": dict(OCR_MODEL_LABELS),
        "emb_model_labels": dict(EMB_MODEL_LABELS),
        "services": [
            {
                "id": "extraction",
                "label": "Извлечение графа (LLM)",
                "config_key": "llm_model",
                "current": cfg.get("llm_model", DEFAULTS["llm_model"]),
            },
            {
                "id": "ingestion_filter",
                "label": "Фильтр чанков при ingestion (LLM)",
                "config_key": "llm_model",
                "current": cfg.get("llm_model", DEFAULTS["llm_model"]),
                "note": "Использует ту же модель, что и извлечение",
            },
            {
                "id": "ocr",
                "label": "OCR (PDF и изображения)",
                "config_key": "ocr_model",
                "current": cfg.get("ocr_model", DEFAULTS["ocr_model"]),
            },
            {
                "id": "embed_doc",
                "label": "Qdrant — индексация (embedding doc)",
                "config_key": "emb_doc_model",
                "current": cfg.get("emb_doc_model", DEFAULTS["emb_doc_model"]),
            },
            {
                "id": "embed_query",
                "label": "Qdrant — поиск (embedding query)",
                "config_key": "emb_query_model",
                "current": cfg.get("emb_query_model", DEFAULTS["emb_query_model"]),
            },
        ],
    }
