"""Синглтон-обёртка над async-драйвером Neo4j."""
from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from mkg_core.config import Settings, get_settings


class Neo4jClient:
    _instance: "Neo4jClient | None" = None

    def __new__(cls, settings: Settings | None = None) -> "Neo4jClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings: Settings | None = None) -> None:
        if self._initialized:
            return
        self.settings = settings or get_settings()
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )
        self._initialized = True

    @classmethod
    def instance(cls) -> "Neo4jClient":
        return cls()

    async def run(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(cypher, params or {})
            return [record.data() async for record in result]

    async def run_write(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self._driver.session(database=self.settings.neo4j_database) as session:
            return await session.execute_write(
                lambda tx: _collect(tx, cypher, params or {})
            )

    async def verify(self) -> bool:
        await self._driver.verify_connectivity()
        return True

    async def clear_all(self) -> None:
        await self.run_write("MATCH (n) DETACH DELETE n")

    async def aclose(self) -> None:
        await self._driver.close()


async def _collect(tx: Any, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = await tx.run(cypher, params)
    return [record.data() async for record in result]
