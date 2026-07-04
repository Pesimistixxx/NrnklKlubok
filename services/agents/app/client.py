from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class GatewayClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        response = await self._client.get(path, params={k: v for k, v in params.items() if v is not None})
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(path, json=body)
        response.raise_for_status()
        return response.json()

    async def capabilities(self) -> dict[str, Any]:
        return await self._get("/api/v1/agents/capabilities")

    async def docs(self, page_size: int) -> dict[str, Any]:
        return await self._get("/api/v1/agents/docs", page=1, page_size=page_size)

    async def search(self, doc_id: str, query: str, limit: int) -> dict[str, Any]:
        doc = quote(doc_id, safe="")
        return await self._post(
            f"/api/v1/agents/documents/{doc}/search",
            {
                "query": query,
                "limit": limit,
                "mode": "auto",
                "layers": ["L3", "L4", "L6"],
                "index_if_missing": False,
            },
        )

    async def nodes(self, doc_id: str, query: str, limit: int) -> dict[str, Any]:
        doc = quote(doc_id, safe="")
        return await self._get(
            f"/api/v1/agents/documents/{doc}/nodes",
            q=query,
            limit=limit,
        )

    async def node(self, doc_id: str, node_id: str) -> dict[str, Any]:
        doc = quote(doc_id, safe="")
        node = quote(node_id, safe="")
        return await self._get(f"/api/v1/agents/documents/{doc}/nodes/{node}")
