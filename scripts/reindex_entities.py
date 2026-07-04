#!/usr/bin/env python3
"""Backfill mkg_entities for the local corpus (run from repo root)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "core" / "src"))

from mkg_core.embeddings import count_indexed_points, reindex_corpus, reindex_corpus_entities
from mkg_core.runtime_config import load_runtime_config


async def main() -> None:
    await load_runtime_config()
    before = await count_indexed_points()
    print("Before:", json.dumps(before, ensure_ascii=False, indent=2))

    entities = await reindex_corpus_entities()
    print("Entities reindex:", json.dumps(entities, ensure_ascii=False, indent=2))

    full = await reindex_corpus()
    print("Full reindex:", json.dumps({
        "documents": full.get("documents"),
        "indexed_l3": full.get("indexed_l3"),
        "indexed_l4": full.get("indexed_l4"),
        "indexed_entities": full.get("indexed_entities"),
        "errors": full.get("errors"),
    }, ensure_ascii=False, indent=2))

    after = await count_indexed_points()
    print("After:", json.dumps(after, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
