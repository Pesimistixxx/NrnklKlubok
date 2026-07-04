"""Единая конфигурация из окружения (.env). Синглтон через lru_cache."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Yandex AI Studio
    yandex_api_key: str = Field(default="", alias="YANDEX_API_KEY")
    yandex_folder_id: str = Field(default="", alias="YANDEX_FOLDER_ID")
    yandex_llm_base_url: str = Field(
        default="https://ai.api.cloud.yandex.net/v1", alias="YANDEX_LLM_BASE_URL"
    )
    yandex_ocr_url: str = Field(
        default="https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText",
        alias="YANDEX_OCR_URL",
    )
    yandex_model_pro: str = Field(default="yandexgpt-5.1", alias="YANDEX_MODEL_PRO")
    yandex_model_lite: str = Field(default="yandexgpt-5-lite", alias="YANDEX_MODEL_LITE")
    yandex_emb_doc: str = Field(default="text-search-doc/latest", alias="YANDEX_EMB_DOC")
    yandex_emb_query: str = Field(
        default="text-search-query/latest", alias="YANDEX_EMB_QUERY"
    )

    # Neo4j
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="neo4j", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")

    # Qdrant
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_collection_chunks: str = Field(
        default="mkg_chunks", alias="QDRANT_COLLECTION_CHUNKS"
    )
    qdrant_collection_claims: str = Field(
        default="mkg_claims", alias="QDRANT_COLLECTION_CLAIMS"
    )
    qdrant_vector_size: int = Field(default=256, alias="QDRANT_VECTOR_SIZE")

    # Postgres / Redis
    database_url: str = Field(
        default="postgresql+asyncpg://mkg:changeme@postgres:5432/mkg",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # App
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    storage_dir: str = Field(default="./data/storage", alias="STORAGE_DIR")
    prompts_path: str = Field(
        default="./packages/prompts/catalog", alias="PROMPTS_PATH"
    )
    default_llm_model: str = Field(default="yandexgpt", alias="DEFAULT_LLM_MODEL")
    max_upload_bytes: int = Field(default=52_428_800, alias="MAX_UPLOAD_BYTES")  # 50 MiB
    auto_extract_after_ingest: bool = Field(default=False, alias="AUTO_EXTRACT_AFTER_INGEST")
    llm_concurrency: int = Field(default=3, alias="LLM_CONCURRENCY")
    llm_cache_enabled: bool = Field(default=True, alias="LLM_CACHE_ENABLED")
    llm_cache_embeddings: bool = Field(default=True, alias="LLM_CACHE_EMBEDDINGS")
    agents_url: str = Field(default="http://agents:8010", alias="AGENTS_URL")
    agents_timeout_seconds: float = Field(default=30.0, alias="AGENTS_TIMEOUT_SECONDS")

    # helpers ------------------------------------------------------------
    def gpt_uri(self, model_name: str) -> str:
        return f"gpt://{self.yandex_folder_id}/{model_name}"

    def emb_uri(self, model_name: str) -> str:
        return f"emb://{self.yandex_folder_id}/{model_name}"

    def asyncpg_dsn(self) -> str:
        """asyncpg принимает postgresql://, не postgresql+asyncpg://."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return "postgresql://" + url.removeprefix("postgresql+asyncpg://")
        return url

    def auth_headers_foundation_api_key(self, *, json_body: bool = True) -> dict[str, str]:
        """Embeddings (Foundation Models): Api-Key + заголовок x-folder-id."""
        headers: dict[str, str] = {}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self.yandex_api_key:
            headers["Authorization"] = f"Api-Key {self.yandex_api_key}"
        if self.yandex_folder_id:
            headers["x-folder-id"] = self.yandex_folder_id
        return headers

    def auth_headers_ocr_vision(self) -> dict[str, str]:
        """OCR Vision: Authorization: Api-Key + x-folder-id."""
        if not self.yandex_api_key:
            raise ValueError("YANDEX_API_KEY обязателен для OCR")
        if not self.yandex_folder_id:
            raise ValueError("YANDEX_FOLDER_ID обязателен для OCR (x-folder-id)")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.yandex_api_key}",
            "x-folder-id": self.yandex_folder_id,
        }

    # совместимость (старые имена)
    def yandex_auth_headers(self, *, json_body: bool = True) -> dict[str, str]:
        return self.auth_headers_foundation_api_key(json_body=json_body)

    def yandex_ocr_auth_headers(self) -> dict[str, str]:
        return self.auth_headers_ocr_vision()


@lru_cache
def get_settings() -> Settings:
    return Settings()
