"""Журнал вызовов LLM/OCR/API по документу (JSONL на диске)."""
from __future__ import annotations

import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mkg_core.config import get_settings

_DOC_CTX: ContextVar[str | None] = ContextVar("pipeline_doc_id", default=None)
_LOCK = threading.Lock()
_MAX_TEXT = 4000


def set_doc_context(doc_id: str | None) -> None:
    _DOC_CTX.set(doc_id)


def get_doc_context() -> str | None:
    return _DOC_CTX.get()


def _logs_dir() -> Path:
    p = Path(get_settings().storage_dir) / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _MAX_TEXT:
        return value[:_MAX_TEXT] + f"\n… (+{len(value) - _MAX_TEXT} симв.)"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value[:50]]
    return value


def log_event(
    kind: str,
    *,
    doc_id: str | None = None,
    request: Any = None,
    response: Any = None,
    error: str | None = None,
    **meta: Any,
) -> None:
    """Записать событие пайплайна (LLM, OCR, HTTP и т.д.)."""
    doc = doc_id or get_doc_context()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "doc_id": doc,
        "request": _clip(request),
        "response": _clip(response),
        "error": error,
        **meta,
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with _LOCK:
        global_path = _logs_dir() / "global.jsonl"
        global_path.open("a", encoding="utf-8").write(line)
        if doc:
            doc_path = _logs_dir() / f"{doc.replace(':', '_')}.jsonl"
            doc_path.open("a", encoding="utf-8").write(line)


def read_logs(doc_id: str | None = None, *, limit: int = 100) -> list[dict[str, Any]]:
    with _LOCK:
        if doc_id:
            path = _logs_dir() / f"{doc_id.replace(':', '_')}.jsonl"
        else:
            path = _logs_dir() / "global.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    items: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items
