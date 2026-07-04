from __future__ import annotations

import re
from typing import Any

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class PromptRenderer:
    def render(self, template: str, params: dict[str, Any]) -> str:
        missing = self.missing_params(template, params)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Missing prompt params: {names}")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            value = params[key]
            return "" if value is None else str(value)

        return _PLACEHOLDER.sub(replace, template)

    def validate_required_params(
        self,
        required_params: tuple[str, ...] | list[str],
        params: dict[str, Any],
    ) -> None:
        missing = {name for name in required_params if name not in params}
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Missing required prompt params: {names}")

    def missing_params(self, template: str, params: dict[str, Any]) -> set[str]:
        required = {match.group(1) for match in _PLACEHOLDER.finditer(template)}
        return {name for name in required if name not in params}
