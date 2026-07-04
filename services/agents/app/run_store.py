"""In-memory store for async orchestrator runs (live trace + graph polling)."""
from __future__ import annotations

import time
import uuid
from typing import Any


_MAX_RUNS = 64
_RUN_TTL_S = 3600

_runs: dict[str, dict[str, Any]] = {}


def _prune() -> None:
    now = time.time()
    stale = [rid for rid, rec in _runs.items() if now - float(rec.get("updated_at") or 0) > _RUN_TTL_S]
    for rid in stale:
        _runs.pop(rid, None)
    if len(_runs) <= _MAX_RUNS:
        return
    ordered = sorted(_runs.items(), key=lambda x: float(x[1].get("updated_at") or 0))
    for rid, _ in ordered[: len(_runs) - _MAX_RUNS]:
        _runs.pop(rid, None)


def create_run() -> str:
    _prune()
    run_id = uuid.uuid4().hex[:16]
    _runs[run_id] = {
        "status": "pending",
        "trace": [],
        "graph": None,
        "layer_results": [],
        "result": None,
        "error": None,
        "updated_at": time.time(),
    }
    return run_id


def update_run(run_id: str, **fields: Any) -> None:
    rec = _runs.get(run_id)
    if not rec:
        return
    rec.update(fields)
    rec["updated_at"] = time.time()


def get_run(run_id: str) -> dict[str, Any] | None:
    return _runs.get(run_id)
