"""Применение схемы Neo4j (constraints/indexes) из schema.cypher.

Запуск: python packages/graph/init_schema.py
Требует .env с NEO4J_* (см. .env.example).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from mkg_core import Neo4jClient

SCHEMA = Path(__file__).parent / "schema.cypher"


def _statements(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.split(";"):
        # убираем построчные комментарии //
        lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("//")]
        stmt = "\n".join(lines).strip()
        if stmt:
            out.append(stmt)
    return out


async def main() -> None:
    client = Neo4jClient.instance()
    await client.verify()
    for stmt in _statements(SCHEMA.read_text(encoding="utf-8")):
        await client.run_write(stmt)
        print("OK:", stmt.splitlines()[0][:70])
    await client.aclose()
    print("Схема применена.")


if __name__ == "__main__":
    asyncio.run(main())
