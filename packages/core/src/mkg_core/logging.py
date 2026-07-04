"""Единая настройка логирования для всех сервисов MKG."""
from __future__ import annotations

import logging
import sys
from typing import Any

_CONFIGURED: set[str] = set()


class _ServiceFilter(logging.Filter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service  # type: ignore[attr-defined]
        return True


def setup_logging(service: str, level: str | None = None) -> logging.Logger:
    """Инициализирует root-logger один раз на процесс для указанного сервиса."""
    from mkg_core.config import get_settings

    if service in _CONFIGURED:
        return logging.getLogger(service)

    log_level = (level or get_settings().log_level or "INFO").upper()
    fmt = "%(asctime)s | %(levelname)-7s | %(service)s | %(name)s | %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.addFilter(_ServiceFilter(service))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    _CONFIGURED.add(service)
    return logging.getLogger(service)


def log_extra(**kwargs: Any) -> dict[str, Any]:
    """Доп. поля для logger.info(..., extra=log_extra(doc_id=...))."""
    return kwargs
