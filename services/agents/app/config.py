from __future__ import annotations

import os
from dataclasses import dataclass

from mkg_core.config import get_settings as get_core_settings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _AgentEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_url: str = Field(default="http://localhost:8000", alias="GATEWAY_URL")
    timeout_seconds: float = Field(default=45.0, alias="AGENTS_TIMEOUT_SECONDS")
    llm_model: str = Field(default="", alias="AGENTS_LLM_MODEL")
    llm_max_output_tokens: int = Field(default=1200, alias="AGENTS_LLM_MAX_OUTPUT_TOKENS")
    max_docs: int = Field(default=5, alias="AGENTS_MAX_DOCS")
    search_limit: int = Field(default=6, alias="AGENTS_SEARCH_LIMIT")
    max_context_nodes: int = Field(default=10, alias="AGENTS_MAX_CONTEXT_NODES")
    max_agent_loops: int = Field(default=1, alias="AGENTS_MAX_AGENT_LOOPS")
    agent_loop_max_rounds: int = Field(default=4, alias="AGENT_LOOP_MAX_ROUNDS")
    agent_loop_min_rounds: int = Field(default=2, alias="AGENT_LOOP_MIN_ROUNDS")
    agent_loop_hard_cap: int = Field(default=6, alias="AGENT_LOOP_HARD_CAP")
    agent_halt_mode: str = Field(default="adaptive", alias="AGENT_HALT_MODE")
    agent_halt_use_llm: bool = Field(default=True, alias="AGENT_HALT_USE_LLM")
    agent_halt_min_gain: int = Field(default=2, alias="AGENT_HALT_MIN_GAIN")
    agent_halt_random: bool = Field(default=True, alias="AGENT_HALT_RANDOM")
    max_hypothesis_refinements: int = Field(default=1, alias="AGENTS_MAX_HYPOTHESIS_REFINEMENTS")
    planner_timeout: float = Field(default=1.2, alias="AGENTS_LLM_PLANNER_TIMEOUT")
    analyzer_timeout: float = Field(default=1.8, alias="AGENTS_LLM_ANALYZER_TIMEOUT")
    builder_timeout: float = Field(default=1.8, alias="AGENTS_LLM_BUILDER_TIMEOUT")


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y", "t"}


def _str_env(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip()


@dataclass(frozen=True)
class AgentSettings:
    gateway_url: str
    timeout_seconds: float
    llm_model: str
    llm_max_output_tokens: int
    max_docs: int
    search_limit: int
    max_context_nodes: int
    max_agent_loops: int
    agent_loop_max_rounds: int
    agent_loop_min_rounds: int
    agent_loop_hard_cap: int
    agent_halt_mode: str
    agent_halt_use_llm: bool
    agent_halt_min_gain: int
    agent_halt_random: bool
    max_hypothesis_refinements: int
    planner_timeout: float
    analyzer_timeout: float
    builder_timeout: float

    @property
    def llm_configured(self) -> bool:
        core = get_core_settings()
        bad_values = {"", "your-yandex-api-key", "your-yandex-folder-id"}
        return core.yandex_api_key not in bad_values and core.yandex_folder_id not in bad_values


def get_agent_settings() -> AgentSettings:
    core = get_core_settings()
    env = _AgentEnv()
    return AgentSettings(
        gateway_url=(os.getenv("GATEWAY_URL") or env.gateway_url).rstrip("/"),
        timeout_seconds=_float_env("AGENTS_TIMEOUT_SECONDS", env.timeout_seconds),
        llm_model=os.getenv("AGENTS_LLM_MODEL") or env.llm_model or core.yandex_model_lite or "yandexgpt-5-lite",
        llm_max_output_tokens=_int_env("AGENTS_LLM_MAX_OUTPUT_TOKENS", env.llm_max_output_tokens),
        max_docs=_int_env("AGENTS_MAX_DOCS", env.max_docs),
        search_limit=_int_env("AGENTS_SEARCH_LIMIT", env.search_limit),
        max_context_nodes=_int_env("AGENTS_MAX_CONTEXT_NODES", env.max_context_nodes),
        max_agent_loops=_int_env("AGENTS_MAX_AGENT_LOOPS", env.max_agent_loops),
        agent_loop_max_rounds=_int_env("AGENT_LOOP_MAX_ROUNDS", env.agent_loop_max_rounds),
        agent_loop_min_rounds=_int_env("AGENT_LOOP_MIN_ROUNDS", env.agent_loop_min_rounds),
        agent_loop_hard_cap=_int_env("AGENT_LOOP_HARD_CAP", env.agent_loop_hard_cap),
        agent_halt_mode=_str_env("AGENT_HALT_MODE", env.agent_halt_mode),
        agent_halt_use_llm=_bool_env("AGENT_HALT_USE_LLM", env.agent_halt_use_llm),
        agent_halt_min_gain=_int_env("AGENT_HALT_MIN_GAIN", env.agent_halt_min_gain),
        agent_halt_random=_bool_env("AGENT_HALT_RANDOM", env.agent_halt_random),
        max_hypothesis_refinements=_int_env("AGENTS_MAX_HYPOTHESIS_REFINEMENTS", env.max_hypothesis_refinements),
        planner_timeout=_float_env("AGENTS_LLM_PLANNER_TIMEOUT", env.planner_timeout),
        analyzer_timeout=_float_env("AGENTS_LLM_ANALYZER_TIMEOUT", env.analyzer_timeout),
        builder_timeout=_float_env("AGENTS_LLM_BUILDER_TIMEOUT", env.builder_timeout),
    )
