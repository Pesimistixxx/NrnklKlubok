"""Синглтон-клиент Yandex AI Studio.

Использует OpenAI-совместимый Responses API (`client.responses.create`) — как в
официальном quickstart Yandex AI Studio. Поддерживает полный набор параметров генерации:
`temperature`, `max_output_tokens`, `top_p`, `reasoning`, `response_format` (structured
output / JSON), `tools`, `parallel_tool_calls`, `seed`, `stream`.

Модель и её параметры под конкретную задачу приходят из PromptRegistry — здесь транспорт.
Секреты и base_url — из Settings (.env).

Docs: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from openai import AsyncOpenAI

from mkg_core.config import Settings, get_settings
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.llm_cache import LLMResponseCache
from mkg_core.llm_usage import cache_hit_usage, extract_llm_usage

try:
    from mkg_core.pipeline_log import log_event
except ImportError:  # pragma: no cover
    def log_event(*args, **kwargs):  # type: ignore[misc]
        pass

_EMBED_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"


class YandexLLMClient:
    """Ленивый синглтон. Один инстанс на процесс."""

    _instance: "YandexLLMClient | None" = None

    def __new__(cls, settings: Settings | None = None) -> "YandexLLMClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings: Settings | None = None) -> None:
        if self._initialized:
            return
        self.settings = settings or get_settings()
        # Официальный quickstart Yandex AI Studio:
        # OpenAI(api_key=..., project=folder_id, base_url=https://ai.api.cloud.yandex.net/v1)
        # OCR (Vision): Api-Key + x-folder-id; LLM — OpenAI SDK + project.
        self._client = AsyncOpenAI(
            api_key=self.settings.yandex_api_key,
            project=self.settings.yandex_folder_id or None,
            base_url=self.settings.yandex_llm_base_url,
            timeout=120.0,
        )
        self._http = httpx.AsyncClient(timeout=120.0)
        self._initialized = True

    @classmethod
    def instance(cls) -> "YandexLLMClient":
        return cls()

    def _resolve_model(self, model: str | None) -> str:
        name = model or self.settings.yandex_model_pro
        return name if name.startswith("gpt://") else self.settings.gpt_uri(name)

    def _build_params(
        self,
        *,
        model: str | None,
        instructions: str,
        input_content: Any,
        temperature: float | None,
        max_output_tokens: int | None,
        top_p: float | None,
        reasoning: dict | str | None,
        response_format: dict | None,
        tools: list | None,
        parallel_tool_calls: bool | None,
        seed: int | None,
        extra: dict | None,
    ) -> dict[str, Any]:
        # Прямые параметры Responses API (принимает OpenAI SDK).
        params: dict[str, Any] = {
            "model": self._resolve_model(model),
            "instructions": instructions,
            "input": input_content,
        }
        if temperature is not None:
            params["temperature"] = temperature
        if max_output_tokens is not None:
            params["max_output_tokens"] = max_output_tokens
        if top_p is not None:
            params["top_p"] = top_p
        if reasoning is not None:  # только Pro-модели
            params["reasoning"] = {"effort": reasoning} if isinstance(reasoning, str) else reasoning
        if tools is not None:
            params["tools"] = tools
            if parallel_tool_calls is not None:
                params["parallel_tool_calls"] = parallel_tool_calls

        # Yandex-специфичные поля пробрасываем в тело запроса через extra_body,
        # т.к. OpenAI SDK не знает про них как про именованные аргументы.
        extra_body: dict[str, Any] = {}
        if response_format is not None:  # structured output / JSON
            extra_body["response_format"] = response_format
        if seed is not None:
            extra_body["seed"] = seed
        if extra:
            extra_body.update(extra)
        if extra_body:
            params["extra_body"] = extra_body
        return params

    # ── основная генерация (Responses API) ─────────────────────────────
    async def generate(
        self,
        instructions: str,
        input_text: str,
        *,
        model: str | None = None,
        temperature: float | None = 0.1,
        max_output_tokens: int | None = 2048,
        top_p: float | None = None,
        reasoning: dict | str | None = None,
        response_format: dict | None = None,
        tools: list | None = None,
        parallel_tool_calls: bool | None = None,
        seed: int | None = None,
        extra: dict | None = None,
    ) -> str:
        params = self._build_params(
            model=model,
            instructions=instructions,
            input_content=input_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            reasoning=reasoning,
            response_format=response_format,
            tools=tools,
            parallel_tool_calls=parallel_tool_calls,
            seed=seed,
            extra=extra,
        )
        req_log = {
            "model": params.get("model"),
            "instructions": instructions,
            "input": input_text,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        cache_payload = {
            "model": params.get("model"),
            "instructions": instructions,
            "input": input_text,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "top_p": top_p,
            "response_format": response_format,
            "seed": seed,
            "reasoning": reasoning,
            "tools": tools,
            "parallel_tool_calls": parallel_tool_calls,
            "extra": extra,
        }
        cache = LLMResponseCache.instance()
        cached = cache.get_text("generate", cache_payload)
        if cached is not None:
            usage = cache_hit_usage()
            log_event(
                "llm",
                request=req_log,
                response={"output_text": cached, "cache_hit": True},
                model=params.get("model"),
                usage=usage,
            )
            return cached
        try:
            resp = await self._client.responses.create(**params)
            text = resp.output_text
            usage = extract_llm_usage(resp)
            cache.set_text("generate", cache_payload, text, model=str(params.get("model") or ""))
            log_event(
                "llm",
                request=req_log,
                response={"output_text": text, "cache_hit": False},
                model=params.get("model"),
                usage=usage,
            )
            return text
        except Exception as exc:
            log_event("llm", request=req_log, error=str(exc), model=params.get("model"))
            raise

    async def generate_json(
        self,
        instructions: str,
        input_text: str,
        *,
        model: str | None = None,
        temperature: float | None = 0.0,
        max_output_tokens: int | None = 4096,
        json_schema: dict | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Генерация со structured output. Если задана json_schema — просим строгий JSON."""
        response_format = (
            {"type": "json_schema", "json_schema": json_schema}
            if json_schema
            else {"type": "json_object"}
        )
        text = await self.generate(
            instructions,
            input_text,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_format=response_format,
            **kwargs,
        )
        return _safe_json(text)

    # ── совместимость с PromptRegistry (system/user + max_tokens) ───────
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        kwargs.pop("with_history", None)
        kwargs.pop("presence_penalty", None)
        return await self.generate(
            system_prompt,
            user_prompt,
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            **kwargs,
        )

    # ── vision (изображение → текст/диаграмма) ─────────────────────────
    async def vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_base64: str,
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        mime: str = "image/png",
    ) -> str:
        input_content = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{image_base64}",
                    },
                ],
            }
        ]
        params = self._build_params(
            model=model,
            instructions=system_prompt,
            input_content=input_content,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=None,
            reasoning=None,
            response_format=None,
            tools=None,
            parallel_tool_calls=None,
            seed=None,
            extra=None,
        )
        req_log = {
            "model": params.get("model"),
            "instructions": system_prompt,
            "user_prompt": user_prompt,
            "mime": mime,
        }
        cache_payload = {
            "model": params.get("model"),
            "instructions": system_prompt,
            "user_prompt": user_prompt,
            "image_sha256": hashlib.sha256(image_base64.encode("utf-8")).hexdigest(),
            "mime": mime,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        cache = LLMResponseCache.instance()
        cached = cache.get_text("vision", cache_payload)
        if cached is not None:
            log_event(
                "llm_vision",
                request=req_log,
                response={"output_text": cached, "cache_hit": True},
                usage=cache_hit_usage(),
            )
            return cached
        try:
            resp = await self._client.responses.create(**params)
            text = resp.output_text
            cache.set_text("vision", cache_payload, text, model=str(params.get("model") or ""))
            log_event(
                "llm_vision",
                request=req_log,
                response={"output_text": text, "cache_hit": False},
                usage=extract_llm_usage(resp),
            )
            return text
        except Exception as exc:
            log_event("llm_vision", request=req_log, error=str(exc))
            raise

    # ── embeddings (нативный endpoint) ─────────────────────────────────
    async def embed(self, text: str, *, kind: str = "doc") -> list[float]:
        from mkg_core.runtime_config import get_emb_doc_model, get_emb_query_model

        model_name = (
            await get_emb_doc_model() if kind == "doc" else await get_emb_query_model()
        )
        model_uri = self.settings.emb_uri(model_name)
        cache_payload = {"model_uri": model_uri, "text": text, "kind": kind}
        cache = LLMResponseCache.instance()
        cached = cache.get_embedding(cache_payload)
        if cached is not None:
            log_event("embed", request={"model_uri": model_uri, "kind": kind}, usage=cache_hit_usage(), cache_hit=True)
            return cached
        payload = {"modelUri": model_uri, "text": text}
        headers = self.settings.auth_headers_foundation_api_key()
        resp = await self._http.post(_EMBED_URL, headers=headers, json=payload)
        resp.raise_for_status()
        body = resp.json()
        embedding = body["embedding"]
        usage = {
            "input_tokens": _int_embed(body.get("inputTokenCount") or body.get("input_tokens")),
            "output_tokens": 0,
            "total_tokens": _int_embed(body.get("inputTokenCount") or body.get("input_tokens")),
            "cached_tokens": 0,
            "cache_hit": False,
        }
        cache.set_embedding(cache_payload, embedding, model=model_uri)
        log_event("embed", request={"model_uri": model_uri, "text_len": len(text), "kind": kind}, usage=usage)
        return embedding

    async def aclose(self) -> None:
        await self._client.close()
        await self._http.aclose()


def _int_embed(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_json(text: str) -> dict[str, Any]:
    """Достаём JSON из ответа модели (на случай обёрток/пояснений)."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise
