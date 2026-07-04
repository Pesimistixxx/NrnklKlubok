#!/usr/bin/env python3
"""Smoke-тест Yandex AI Studio — как в официальном quickstart.

Запуск (из корня репозитория, с заполненным .env):

    pip install --upgrade openai pydantic-settings
    python scripts/yandex_llm_smoke.py

Или с переменными окружения:

    set YANDEX_API_KEY=...
    set YANDEX_FOLDER_ID=...
    python scripts/yandex_llm_smoke.py
"""
from __future__ import annotations

import os
import sys

from openai import OpenAI


def main() -> int:
    folder_id = os.environ.get("YANDEX_FOLDER_ID", "").strip()
    api_key = os.environ.get("YANDEX_API_KEY", "").strip()
    base_url = os.environ.get("YANDEX_LLM_BASE_URL", "https://ai.api.cloud.yandex.net/v1").strip()
    model_name = os.environ.get("YANDEX_SMOKE_MODEL", "aliceai-llm").strip()

    if not folder_id or not api_key:
        print("Задайте YANDEX_FOLDER_ID и YANDEX_API_KEY в .env или окружении", file=sys.stderr)
        return 1

    client = OpenAI(
        api_key=api_key,
        project=folder_id,
        base_url=base_url,
    )

    response = client.responses.create(
        model=f"gpt://{folder_id}/{model_name}",
        input="Придумай 3 необычные идеи для стартапа в сфере путешествий.",
        temperature=0.8,
        max_output_tokens=1500,
    )

    text = getattr(response, "output_text", None)
    if not text and response.output:
        text = response.output[0].content[0].text
    print(text or response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
