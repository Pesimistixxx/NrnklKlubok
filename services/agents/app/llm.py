from __future__ import annotations

import asyncio
import json
from typing import Any

from mkg_core.llm import YandexLLMClient


class AgentLLM:
    def __init__(self, model: str) -> None:
        self.model = model
        self._client = YandexLLMClient.instance()

    async def generate_json(
        self,
        *,
        instructions: str,
        payload: dict[str, Any],
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any]:
        input_text = json.dumps(payload, ensure_ascii=False)
        return await asyncio.wait_for(
            self._client.generate_json(
                instructions,
                input_text,
                model=self.model,
                temperature=0.0,
                max_output_tokens=max_tokens,
            ),
            timeout=max(0.2, timeout),
        )
