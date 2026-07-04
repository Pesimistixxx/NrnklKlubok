"""Синглтон Qdrant: коллекции чанков, утверждений (Claim) и сущностей L1."""
from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from mkg_core.config import Settings, get_settings


class QdrantClientSingleton:
    _instance: "QdrantClientSingleton | None" = None

    def __new__(cls, settings: Settings | None = None) -> "QdrantClientSingleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings: Settings | None = None) -> None:
        if self._initialized:
            return
        self.settings = settings or get_settings()
        self.client = AsyncQdrantClient(
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key or None,
        )
        self._initialized = True

    @classmethod
    def instance(cls) -> "QdrantClientSingleton":
        return cls()

    async def ensure_collections(self) -> None:
        size = self.settings.qdrant_vector_size
        for name in (
            self.settings.qdrant_collection_chunks,
            self.settings.qdrant_collection_claims,
            self.settings.qdrant_collection_entities,
        ):
            exists = await self.client.collection_exists(name)
            if not exists:
                await self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=size, distance=Distance.COSINE),
                )
