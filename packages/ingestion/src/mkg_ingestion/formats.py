"""Реестр поддерживаемых форматов загрузки."""
from __future__ import annotations

from pathlib import Path

# ext -> категория маршрутизации ingestion
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "ocr",
    ".png": "ocr",
    ".jpg": "ocr",
    ".jpeg": "ocr",
    ".webp": "ocr",
    ".bmp": "ocr",
    ".tiff": "ocr",
    ".tif": "ocr",
    ".md": "markdown",
    ".txt": "text",
    ".csv": "csv",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".docx": "docx",
    ".xlsx": "xlsx",
}

MIME_BY_EXT: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".xml": "application/xml",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MiB


def extension(file_name: str) -> str:
    return Path(file_name).suffix.lower()


def detect_route(file_name: str) -> str:
    ext = extension(file_name)
    return SUPPORTED_EXTENSIONS.get(ext, "unknown")


def mime_type(file_name: str) -> str:
    ext = extension(file_name)
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def is_supported(file_name: str) -> bool:
    return extension(file_name) in SUPPORTED_EXTENSIONS


def is_binary(file_name: str) -> bool:
    route = detect_route(file_name)
    return route in {"ocr", "docx", "xlsx"}


def validate_upload(file_name: str, size_bytes: int, *, max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES) -> None:
    """ValueError с понятным текстом при неверном файле."""
    name = (file_name or "").strip()
    if not name:
        raise ValueError("Имя файла пустое")
    ext = extension(name)
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Формат «{ext or 'без расширения'}» не поддерживается. Допустимо: {allowed}")
    if size_bytes <= 0:
        raise ValueError("Файл пустой")
    if size_bytes > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise ValueError(f"Файл слишком большой (макс. {mb:.0f} МБ)")


def formats_public(*, max_bytes: int | None = None) -> dict:
    """Ответ для API /formats."""
    if max_bytes is None:
        try:
            from mkg_core import get_settings
            max_bytes = get_settings().max_upload_bytes
        except Exception:
            max_bytes = DEFAULT_MAX_UPLOAD_BYTES
    groups: dict[str, list[str]] = {}
    for ext, route in SUPPORTED_EXTENSIONS.items():
        groups.setdefault(route, []).append(ext)
    return {
        "extensions": sorted(SUPPORTED_EXTENSIONS.keys()),
        "max_size_bytes": max_bytes,
        "groups": groups,
    }
