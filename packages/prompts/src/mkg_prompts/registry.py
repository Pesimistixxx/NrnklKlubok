from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mkg_prompts.models import OPTION_FIELDS, TEMPLATE_FIELDS
from mkg_prompts.renderer import PromptRenderer

_DEFAULT_MODEL_ALIASES: dict[str, str] = {
    "yandexgpt-5.1": "yandexgpt",
    "yandexgpt-5-lite": "yandexgpt",
    "yandexgpt": "yandexgpt",
    "aliceai-llm": "yandexgpt",
}

_MODEL_ALIASES: dict[str, str] = dict(_DEFAULT_MODEL_ALIASES)


def make_prompt_key(stage: str, prompt_type: str, goal: str | None = None) -> str:
    if goal:
        return f"{stage}.{prompt_type}.{goal}"
    return f"{stage}.{prompt_type}"


def parse_prompt_key(key: str) -> tuple[str, str, str | None]:
    parts = key.split(".")
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise ValueError(f"Invalid prompt key {key!r}. Expected stage.type or stage.type.goal")


def _is_prompt_config(node: dict[str, Any]) -> bool:
    return "system_prompt" in node


class PromptRegistry:
    """Singleton: каталог промптов MKG (ingestion / extraction)."""

    _instance: PromptRegistry | None = None
    model: str

    def __new__(cls, prompts_path: str | Path | None = None, *, model: str | None = None) -> PromptRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, prompts_path: str | Path | None = None, *, model: str | None = None) -> None:
        if prompts_path is None and model is None:
            if not self._initialized:
                raise ValueError(
                    "PromptRegistry is not configured. "
                    "Call PromptRegistry.configure(path, model='yandexgpt-5.1')."
                )
            return

        if prompts_path is not None:
            path = Path(prompts_path)
            if self._initialized and getattr(self, "_path", None) == path and (
                model is None or model == self.model
            ):
                return

            self._path = path
            data = self._load(path)
            self._stages: dict[str, Any] = data.get("stages", {})
            self._prompts = self._index_stages(self._stages)
            self._renderer = PromptRenderer()
            self._initialized = True

        if model is not None:
            self.model = model
        elif not hasattr(self, "model"):
            self.model = "yandexgpt-5.1"

    @classmethod
    def configure(cls, prompts_path: str | Path, *, model: str) -> PromptRegistry:
        return cls(prompts_path, model=model)

    @classmethod
    def instance(cls) -> PromptRegistry:
        return cls()

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def get(
        self,
        key: str | None = None,
        params: dict[str, Any] | None = None,
        *,
        stage: str | None = None,
        prompt_type: str | None = None,
        goal: str | None = None,
        model: str | None = None,
        **data: Any,
    ) -> dict[str, Any]:
        if key is not None:
            stage_name, type_name, goal_name = parse_prompt_key(key)
        elif stage and prompt_type:
            stage_name, type_name, goal_name = stage, prompt_type, goal
        else:
            raise ValueError("Pass key or stage + prompt_type (+ optional goal).")

        resolved_key = make_prompt_key(stage_name, type_name, goal_name)
        resolved_model = model or self.model

        models_map = self._prompts.get(resolved_key)
        if models_map is None:
            raise KeyError(
                f"Prompt not found for key={resolved_key!r}. Known keys: {sorted(self._prompts)}"
            )

        raw = self._resolve_prompt_config(models_map, resolved_model)
        if raw is None:
            raise KeyError(
                f"No prompt for model={resolved_model!r} at key={resolved_key!r}. "
                f"Available models: {sorted(models_map)}"
            )

        runtime = {**(params or {}), **data}
        options = {name: runtime.pop(name) for name in OPTION_FIELDS if name in runtime}

        required = list(raw.get("required_params", []))
        self._renderer.validate_required_params(required, runtime)

        result: dict[str, Any] = {}
        for name in TEMPLATE_FIELDS:
            template = raw.get(name)
            if template is None:
                continue
            result[name] = self._renderer.render(str(template), runtime)

        for name in OPTION_FIELDS:
            if name in options:
                result[name] = options[name]
            elif name in raw:
                result[name] = raw[name]

        return result

    def list_stages(self) -> list[str]:
        return sorted(self._stages)

    def list_types(self, stage: str) -> list[str]:
        return sorted(self._require_stage(stage))

    def list_models(self, stage: str, prompt_type: str) -> list[str]:
        return sorted(self._require_type(stage, prompt_type))

    def list_goals(self, stage: str, prompt_type: str, *, model: str | None = None) -> list[str]:
        models_node = self._require_type(stage, prompt_type)
        resolved_model = model or self.model
        model_node = models_node.get(resolved_model)
        if model_node is None:
            alias = _MODEL_ALIASES.get(resolved_model)
            model_node = models_node.get(alias) if alias else None
        if model_node is None:
            raise KeyError(f"No prompts for model={resolved_model!r} at {stage}.{prompt_type}")
        if _is_prompt_config(model_node):
            return []
        return sorted(model_node)

    def list_keys(self, *, model: str | None = None) -> list[str]:
        resolved_model = model or self.model
        keys: list[str] = []
        for key, models_map in self._prompts.items():
            if resolved_model in models_map:
                keys.append(key)
                continue
            alias = _MODEL_ALIASES.get(resolved_model)
            if alias and alias in models_map:
                keys.append(key)
        return sorted(keys)

    def _resolve_prompt_config(self, models_map: dict[str, Any], model: str) -> dict[str, Any] | None:
        if model in models_map:
            return models_map[model]
        alias = _MODEL_ALIASES.get(model)
        if alias and alias in models_map:
            return models_map[alias]
        return None

    def _require_stage(self, stage: str) -> dict[str, Any]:
        node = self._stages.get(stage)
        if node is None:
            raise KeyError(f"Stage not found: {stage!r}")
        return node

    def _require_type(self, stage: str, prompt_type: str) -> dict[str, Any]:
        node = self._require_stage(stage).get(prompt_type)
        if node is None:
            raise KeyError(f"Type not found: {stage}.{prompt_type}")
        return node

    @staticmethod
    def _index_stages(stages: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
        prompts: dict[str, dict[str, dict[str, Any]]] = {}

        for stage, types_node in stages.items():
            if not isinstance(types_node, dict):
                raise ValueError(f"Invalid stage node for {stage!r}")

            for prompt_type, models_node in types_node.items():
                if not isinstance(models_node, dict):
                    raise ValueError(f"Invalid type node for {stage}.{prompt_type}")

                for model_name, model_node in models_node.items():
                    if not isinstance(model_node, dict):
                        raise ValueError(f"Invalid model node for {stage}.{prompt_type}.{model_name}")

                    if _is_prompt_config(model_node):
                        key = make_prompt_key(stage, prompt_type)
                        prompts.setdefault(key, {})[model_name] = model_node
                        continue

                    for goal, config in model_node.items():
                        if not _is_prompt_config(config):
                            raise ValueError(
                                f"Invalid prompt config for {stage}.{prompt_type}.{model_name}.{goal}"
                            )
                        key = make_prompt_key(stage, prompt_type, goal)
                        prompts.setdefault(key, {})[model_name] = config

        return prompts

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if path.is_dir():
            return PromptRegistry._load_catalog(path)
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        if "stages" not in data:
            raise ValueError(f"Invalid prompts file (no 'stages'): {path}")
        return data

    @staticmethod
    def _load_catalog(catalog_dir: Path) -> dict[str, Any]:
        global _MODEL_ALIASES
        _MODEL_ALIASES = dict(_DEFAULT_MODEL_ALIASES)

        meta_path = catalog_dir / "_meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            _MODEL_ALIASES.update(meta.get("model_aliases", {}))

        stages: dict[str, Any] = {}
        for stage_dir in sorted(catalog_dir.iterdir()):
            if not stage_dir.is_dir() or stage_dir.name.startswith("_"):
                continue
            stage_name = stage_dir.name
            stages[stage_name] = {}
            for prompt_file in sorted(stage_dir.glob("*.json")):
                payload = json.loads(prompt_file.read_text(encoding="utf-8"))
                # Файл может быть { "models": { "yandexgpt": {...} } } или напрямую { "yandexgpt": {...} }
                models = payload.get("models", payload)
                stages[stage_name][prompt_file.stem] = models

        if not stages:
            raise ValueError(f"Prompt catalog is empty: {catalog_dir}")
        return {"stages": stages}
