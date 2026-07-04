from __future__ import annotations

from typing import Any, TypedDict

TEMPLATE_FIELDS = ("system_prompt", "user_prompt", "content")
OPTION_FIELDS = (
    "with_history",
    "presence_penalty",
    "max_tokens",
    "max_output_tokens",
    "temperature",
    "top_p",
    "reasoning",
    "response_format",
    "seed",
)

PROMPT_FIELDS = frozenset({*TEMPLATE_FIELDS, *OPTION_FIELDS})


class PromptPayload(TypedDict, total=False):
    system_prompt: str
    user_prompt: str
    content: str
    with_history: bool
    presence_penalty: float
    max_tokens: int
    max_output_tokens: int
    temperature: float
    top_p: float
    reasoning: Any
    response_format: Any
    seed: int
