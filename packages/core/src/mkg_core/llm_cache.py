"""Дисковый кэш ответов LLM / embeddings — экономия на повторных запросах.

Ключ = SHA-256(canonical JSON параметров запроса). Хранение: {STORAGE_DIR}/llm_cache/.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mkg_core.config import get_settings


class LLMResponseCache:
    _instance: "LLMResponseCache | None" = None

    def __new__(cls) -> "LLMResponseCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self) -> None:
        if self._ready:
            return
        settings = get_settings()
        self.enabled = settings.llm_cache_enabled
        self.cache_embeddings = settings.llm_cache_embeddings
        self.root = Path(settings.storage_dir) / "llm_cache"
        self._lock = threading.Lock()
        for sub in ("generate", "embed", "vision"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self._ready = True

    @classmethod
    def instance(cls) -> "LLMResponseCache":
        return cls()

    @staticmethod
    def _digest(kind: str, payload: dict[str, Any]) -> str:
        raw = json.dumps({"kind": kind, **payload}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _path(self, kind: str, digest: str) -> Path:
        return self.root / kind / digest[:2] / f"{digest}.json"

    def get_text(self, kind: str, payload: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        path = self._path(kind, self._digest(kind, payload))
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            text = data.get("output_text")
            return str(text) if text is not None else None
        except Exception:
            return None

    def set_text(self, kind: str, payload: dict[str, Any], text: str, *, model: str = "") -> None:
        if not self.enabled:
            return
        digest = self._digest(kind, payload)
        path = self._path(kind, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "output_text": text,
        }
        with self._lock:
            path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")

    def get_embedding(self, payload: dict[str, Any]) -> list[float] | None:
        if not self.enabled or not self.cache_embeddings:
            return None
        path = self._path("embed", self._digest("embed", payload))
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            vec = data.get("embedding")
            return [float(x) for x in vec] if isinstance(vec, list) else None
        except Exception:
            return None

    def set_embedding(self, payload: dict[str, Any], embedding: list[float], *, model: str = "") -> None:
        if not self.enabled or not self.cache_embeddings:
            return
        digest = self._digest("embed", payload)
        path = self._path("embed", digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "embedding": embedding,
        }
        with self._lock:
            path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")

    def clear_all(self) -> int:
        count = 0
        if not self.root.exists():
            return 0
        for sub in ("generate", "embed", "vision"):
            d = self.root / sub
            if d.exists():
                count += sum(1 for _ in d.rglob("*.json"))
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(parents=True, exist_ok=True)
        return count
