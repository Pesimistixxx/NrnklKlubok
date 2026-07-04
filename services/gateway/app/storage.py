"""Реэкспорт общего реестра документов из mkg_core (общий том с worker)."""
from mkg_core.store import DocumentRepository, get_repo

__all__ = ["DocumentRepository", "get_repo"]
