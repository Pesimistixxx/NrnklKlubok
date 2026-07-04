from __future__ import annotations

import argparse
import json
import mimetypes
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".md",
    ".txt",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".docx",
    ".xlsx",
}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def iter_files(root: Path) -> list[Path]:
    return sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p).lower())


def load_done(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()
    done: set[str] = set()
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") == "uploaded" and item.get("relative_path"):
            done.add(item["relative_path"])
    return done


def append_log(log_path: Path, payload: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def multipart_body(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = f"----mkg-upload-{uuid.uuid4().hex}"
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    parts.append(header)
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), boundary


def upload_one(base_url: str, root: Path, file_path: Path, timeout: int) -> dict:
    rel = file_path.relative_to(root).as_posix()
    source_location = str(file_path.parent.relative_to(root)).replace("\\", "/")
    if source_location == ".":
        source_location = root.name
    else:
        source_location = f"{root.name}/{source_location}"

    body, boundary = multipart_body(
        {
            "classification": "открытый",
            "processing_mode": "full",
            "source_location": source_location,
        },
        file_path,
    )
    req = Request(
        urljoin(base_url.rstrip("/") + "/", "api/v1/documents"),
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw else {}
        return {
            "status": "uploaded",
            "relative_path": rel,
            "document_id": data.get("id"),
            "file_name": data.get("file_name"),
            "remote_status": data.get("status"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Recursively upload MKG source documents.")
    parser.add_argument("--root", default=r"C:\tema\Code\хакатон\mkg\Источники информации")
    parser.add_argument("--base-url", default="https://win.regqwe.ru/")
    parser.add_argument("--log", default=r"C:\tema\Code\хакатон\mkg\data\storage\upload_sources_log.jsonl")
    parser.add_argument("--sleep", type=float, default=60.0)
    parser.add_argument("--error-sleep", type=float, default=180.0)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    root = Path(args.root)
    log_path = Path(args.log)
    done = load_done(log_path)
    files = iter_files(root)

    print(f"root={root}")
    print(f"base_url={args.base_url}")
    print(f"files_total={len(files)} already_uploaded={len(done)}")

    uploaded = skipped = failed = 0
    for file_path in files:
        rel = file_path.relative_to(root).as_posix()
        size = file_path.stat().st_size
        suffix = file_path.suffix.lower()

        if rel in done:
            skipped += 1
            continue
        if suffix not in SUPPORTED_EXTENSIONS:
            skipped += 1
            append_log(log_path, {"status": "skipped_unsupported", "relative_path": rel, "extension": suffix})
            continue
        if size > MAX_UPLOAD_BYTES:
            skipped += 1
            append_log(log_path, {"status": "skipped_too_large", "relative_path": rel, "bytes": size})
            continue

        try:
            result = upload_one(args.base_url, root, file_path, args.timeout)
            uploaded += 1
            append_log(log_path, result | {"bytes": size})
            print(f"UPLOADED {uploaded}: {rel} -> {result.get('document_id')}", flush=True)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            failed += 1
            append_log(log_path, {"status": "failed_http", "relative_path": rel, "code": exc.code, "body": body[:1000]})
            print(f"FAILED HTTP {exc.code}: {rel}: {body[:300]}", flush=True)
            if exc.code in {408, 425, 429, 500, 502, 503, 504}:
                print(f"PAUSE after HTTP {exc.code}: {args.error_sleep:.0f}s", flush=True)
                time.sleep(args.error_sleep)
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            failed += 1
            append_log(log_path, {"status": "failed", "relative_path": rel, "error": str(exc)})
            print(f"FAILED: {rel}: {exc}", flush=True)
            print(f"PAUSE after error: {args.error_sleep:.0f}s", flush=True)
            time.sleep(args.error_sleep)

        time.sleep(args.sleep)

    print(f"done uploaded={uploaded} skipped={skipped} failed={failed} log={log_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
