"""Реестр документов (MVP): файлы на диске + JSON-реестр.

Общий для gateway и worker (общий том STORAGE_DIR). Используется как fallback,
пока основная мета-информация хранится в Postgres (`meta_db.py`).
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mkg_core.config import get_settings


class DocumentRepository:
    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self.base = Path(base_dir or settings.storage_dir)
        self.files = self.base / "files"
        self.md = self.base / "md"
        self.md_raw = self.base / "md_raw"
        self.graph = self.base / "graph"
        self.files.mkdir(parents=True, exist_ok=True)
        self.md.mkdir(parents=True, exist_ok=True)
        self.md_raw.mkdir(parents=True, exist_ok=True)
        self.graph.mkdir(parents=True, exist_ok=True)
        self._registry = self.base / "registry.json"
        self._lock = threading.Lock()
        if not self._registry.exists():
            self._registry.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, dict[str, Any]]:
        return json.loads(self._registry.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self._registry.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def create(
        self,
        file_name: str,
        content: bytes,
        *,
        classification: str = "открытый",
        organization: str | None = None,
        processing_mode: str = "full",
        source_location: str | None = None,
        geography: str | None = None,
        material_date: str | None = None,
        tags: list[str] | None = None,
        ingested_at: str | None = None,
    ) -> dict[str, Any]:
        hash_sum = hashlib.sha256(content).hexdigest()
        doc_id = f"doc:{hash_sum[:16]}"
        with self._lock:
            data = self._load()
            if doc_id in data:  # идемпотентность по контрольной сумме
                return data[doc_id]
            stored_name = f"{doc_id.replace(':', '_')}_{file_name}"
            (self.files / stored_name).write_bytes(content)
            record = {
                "id": doc_id,
                "file_name": file_name,
                "doc_type": None,
                "mime_type": None,
                "classification": classification,
                "organization": organization,
                "processing_mode": processing_mode if processing_mode in ("full", "answers_only") else "full",
                "hash_sum": hash_sum,
                "status": "uploaded",
                "upload_date": datetime.now(timezone.utc).isoformat(),
                "size_bytes": len(content),
                "stored_name": stored_name,
            }
            if source_location:
                record["source_location"] = source_location
            if geography:
                record["geography"] = geography
            if material_date:
                record["material_date"] = material_date
            if tags:
                record["tags"] = list(tags)
            if ingested_at:
                record["ingested_at"] = ingested_at
            else:
                record["ingested_at"] = record["upload_date"]
            data[doc_id] = record
            self._save(data)
            return record

    def get(self, doc_id: str) -> dict[str, Any] | None:
        return self._load().get(doc_id)

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        geography: str | None = None,
        material_year: int | None = None,
        classifications: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        items = sorted(self._load().values(), key=lambda r: r["upload_date"], reverse=True)
        if geography:
            items = [r for r in items if r.get("geography") == geography]
        if material_year is not None:
            items = [
                r
                for r in items
                if str(r.get("material_date") or "")[:4] == str(material_year)
            ]
        if classifications:
            allowed = set(classifications)
            items = [
                r
                for r in items
                if (r.get("classification") or "открытый") in allowed
            ]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def count_restricted(
        self,
        *,
        geography: str | None = None,
        material_year: int | None = None,
        allowed_classifications: list[str] | None = None,
    ) -> int:
        if not allowed_classifications:
            return 0
        allowed = set(allowed_classifications)
        items = list(self._load().values())
        if geography:
            items = [r for r in items if r.get("geography") == geography]
        if material_year is not None:
            items = [
                r
                for r in items
                if str(r.get("material_date") or "")[:4] == str(material_year)
            ]
        return sum(
            1
            for r in items
            if (r.get("classification") or "открытый") not in allowed
        )

    def set_status(self, doc_id: str, status: str, **extra: Any) -> None:
        with self._lock:
            data = self._load()
            if doc_id in data:
                data[doc_id]["status"] = status
                data[doc_id].update(extra)
                self._save(data)

    def delete_graph(self, doc_id: str) -> None:
        path = self.graph / f"{doc_id.replace(':', '_')}.json"
        if path.exists():
            path.unlink(missing_ok=True)

    def request_cancel_extraction(self, doc_id: str) -> None:
        with self._lock:
            data = self._load()
            if doc_id in data:
                data[doc_id]["cancel_requested"] = True
                data[doc_id]["step"] = "cancelling"
                self._save(data)

    def clear_cancel_extraction(self, doc_id: str) -> None:
        with self._lock:
            data = self._load()
            if doc_id in data:
                data[doc_id]["cancel_requested"] = False
                self._save(data)

    def is_cancel_requested(self, doc_id: str) -> bool:
        rec = self.get(doc_id)
        return bool(rec and rec.get("cancel_requested"))

    def markdown_filename(self, doc_id: str) -> str:
        return f"{doc_id.replace(':', '_')}.md"

    def markdown_relative_path(self, doc_id: str) -> str:
        return f"md/{self.markdown_filename(doc_id)}"

    def marked_markdown_relative_path(self, doc_id: str) -> str:
        return f"md_marked/{self.markdown_filename(doc_id)}"

    def raw_markdown_relative_path(self, doc_id: str) -> str:
        return f"md_raw/{self.markdown_filename(doc_id)}"

    def save_markdown(self, doc_id: str, markdown: str) -> None:
        (self.md / self.markdown_filename(doc_id)).write_text(markdown, encoding="utf-8")

    def save_raw_markdown(self, doc_id: str, markdown: str) -> None:
        (self.md_raw / self.markdown_filename(doc_id)).write_text(markdown, encoding="utf-8")

    def save_marked_markdown(self, doc_id: str, markdown: str) -> None:
        marked_dir = self.base / "md_marked"
        marked_dir.mkdir(parents=True, exist_ok=True)
        (marked_dir / self.markdown_filename(doc_id)).write_text(markdown, encoding="utf-8")

    def read_marked_markdown(self, doc_id: str) -> str | None:
        path = self.base / "md_marked" / self.markdown_filename(doc_id)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def read_markdown(self, doc_id: str) -> str | None:
        path = self.md / self.markdown_filename(doc_id)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def read_raw_markdown(self, doc_id: str) -> str | None:
        path = self.md_raw / self.markdown_filename(doc_id)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def read_source(self, doc_id: str) -> bytes | None:
        rec = self.get(doc_id)
        if not rec:
            return None
        path = self.files / rec["stored_name"]
        return path.read_bytes() if path.exists() else None

    def save_graph(self, doc_id: str, payload: dict[str, Any]) -> None:
        path = self.graph / f"{doc_id.replace(':', '_')}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def read_graph(self, doc_id: str) -> dict[str, Any] | None:
        path = self.graph / f"{doc_id.replace(':', '_')}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def clear_all(self) -> dict[str, int]:
        """Удалить все документы, markdown, графы и логи с диска."""
        counts = {"files": 0, "markdown": 0, "raw_markdown": 0, "marked_markdown": 0, "graphs": 0, "logs": 0}
        with self._lock:
            for path in self.files.iterdir():
                if path.is_file():
                    path.unlink(missing_ok=True)
                    counts["files"] += 1
            for path in self.md.iterdir():
                if path.is_file():
                    path.unlink(missing_ok=True)
                    counts["markdown"] += 1
            if self.md_raw.exists():
                for path in self.md_raw.iterdir():
                    if path.is_file():
                        path.unlink(missing_ok=True)
                        counts["raw_markdown"] += 1
            marked_dir = self.base / "md_marked"
            if marked_dir.exists():
                for path in marked_dir.iterdir():
                    if path.is_file():
                        path.unlink(missing_ok=True)
                        counts["marked_markdown"] += 1
            for path in self.graph.iterdir():
                if path.is_file():
                    path.unlink(missing_ok=True)
                    counts["graphs"] += 1
            logs_dir = self.base / "logs"
            if logs_dir.exists():
                for path in logs_dir.iterdir():
                    if path.is_file():
                        path.unlink(missing_ok=True)
                        counts["logs"] += 1
            self._save({})
        return counts


_repo: DocumentRepository | None = None


def get_repo() -> DocumentRepository:
    global _repo
    if _repo is None:
        _repo = DocumentRepository()
    return _repo
