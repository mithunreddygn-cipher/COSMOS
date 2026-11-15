"""Investigation-scoped local storage for uploaded scientific products."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT_ENV = "COSMOS_PRODUCT_STORAGE"
RETENTION_ENV = "COSMOS_PRODUCT_RETENTION_DAYS"
CHUNK_SIZE = 1024 * 1024
DEFAULT_RETENTION_DAYS = 30
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

# Manifest updates are read-modify-write operations.  Keep locks in-process
# and scoped per investigation so unrelated investigations do not block each
# other.  RLock permits update_product() to call product_record() safely.
_LOCKS_GUARD = threading.Lock()
_INVESTIGATION_LOCKS: dict[str, threading.RLock] = {}


def _lock_for(investigation_id: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _INVESTIGATION_LOCKS.setdefault(investigation_id, threading.RLock())


@contextmanager
def _manifest_lock(investigation_id: str):
    lock = _lock_for(investigation_id)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


class ProductStorageError(RuntimeError):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def storage_root() -> Path:
    value = os.environ.get(ROOT_ENV)
    root = Path(value) if value else Path("records") / "investigations"
    return root.resolve()


def validate_id(value: str, label: str = "identifier") -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ProductStorageError(f"Invalid {label}.", 422)
    return value


def investigation_root(investigation_id: str) -> Path:
    validate_id(investigation_id, "investigation ID")
    root = storage_root() / investigation_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _manifest_path(investigation_id: str) -> Path:
    return investigation_root(investigation_id) / "manifest.json"


def _read_manifest(investigation_id: str) -> dict[str, Any]:
    path = _manifest_path(investigation_id)
    if not path.exists():
        raise ProductStorageError("Investigation was not found.", 404)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductStorageError(f"Investigation manifest could not be read: {exc}") from exc


def _write_manifest(investigation_id: str, manifest: dict[str, Any]) -> None:
    root = investigation_root(investigation_id)
    temporary = root / f".manifest-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    target = root / "manifest.json"
    try:
        temporary.replace(target)
    except PermissionError:
        # Some managed Windows sandboxes deny atomic replacement; retain the
        # same scoped target with a safe write fallback.
        target.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8")
        temporary.unlink(missing_ok=True)


def create_investigation(investigation_id: str) -> dict[str, Any]:
    validate_id(investigation_id, "investigation ID")
    with _manifest_lock(investigation_id):
        root = investigation_root(investigation_id)
        manifest = {
            "investigation_id": investigation_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "storage_root": str(root),
            "products": [],
            "processing_status": "RECEIVING",
        }
        _write_manifest(investigation_id, manifest)
        return manifest


def _safe_filename(original_name: str | None, product_id: str) -> str:
    original = Path(original_name or "upload.fits").name
    suffix = Path(original).suffix.lower()
    if suffix not in {".fits", ".fit", ".fts", ".csv", ".ecsv", ".vot", ".votable", ".json"}:
        suffix = ".bin"
    return f"{product_id}{suffix}"


def persist_stream(investigation_id: str, original_name: str | None, chunks: Iterable[bytes]) -> dict[str, Any]:
    """Persist chunks without buffering the complete upload in memory."""
    product_id = uuid.uuid4().hex
    filename = _safe_filename(original_name, product_id)
    root = investigation_root(investigation_id)
    destination = root / filename
    digest = hashlib.sha256()
    size = 0
    temporary = root / f"upload-{product_id}.tmp"
    try:
        with temporary.open("wb") as handle:
            for chunk in chunks:
                if not chunk:
                    continue
                digest.update(chunk)
                size += len(chunk)
                handle.write(chunk)
        temporary.replace(destination)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ProductStorageError(f"Product could not be persisted: {exc}") from exc
    record = {
        "product_id": product_id,
        "original_filename": Path(original_name or "upload.fits").name,
        "filename": filename,
        "relative_path": filename,
        "sha256": digest.hexdigest(),
        "size_bytes": size,
        "stored_at_utc": datetime.now(timezone.utc).isoformat(),
        "format": Path(original_name or "").suffix.lower().lstrip("."),
        "processing_status": "PERSISTED",
        "metadata": {},
        "measurements": [],
    }
    with _manifest_lock(investigation_id):
        manifest = _read_manifest(investigation_id)
        manifest["products"].append(record)
        _write_manifest(investigation_id, manifest)
    return record


async def persist_upload(investigation_id: str, upload: Any, *, max_bytes: int, chunk_size: int = CHUNK_SIZE) -> dict[str, Any]:
    """Persist an UploadFile incrementally and enforce its individual byte limit."""
    product_id = uuid.uuid4().hex
    filename = _safe_filename(getattr(upload, "filename", None), product_id)
    root = investigation_root(investigation_id)
    destination = root / filename
    temporary = root / f"upload-{product_id}.tmp"
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as handle:
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    if max_bytes < 1024 * 1024:
                        limit = f"{max_bytes} bytes"
                    else:
                        limit = f"{max_bytes / (1024 * 1024):g} MiB"
                    raise ProductStorageError(f"Product exceeds the {limit} per-file limit.", 413)
                digest.update(chunk)
                handle.write(chunk)
        temporary.replace(destination)
    except ProductStorageError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ProductStorageError(f"Product could not be persisted: {exc}") from exc
    record = {
        "product_id": product_id,
        "original_filename": Path(getattr(upload, "filename", None) or "upload.fits").name,
        "filename": filename,
        "relative_path": filename,
        "sha256": digest.hexdigest(),
        "size_bytes": size,
        "stored_at_utc": datetime.now(timezone.utc).isoformat(),
        "format": Path(getattr(upload, "filename", None) or "").suffix.lower().lstrip("."),
        "processing_status": "PERSISTED",
        "metadata": {},
        "measurements": [],
    }
    with _manifest_lock(investigation_id):
        manifest = _read_manifest(investigation_id)
        manifest["products"].append(record)
        _write_manifest(investigation_id, manifest)
    return record


def product_record(investigation_id: str, product_id: str) -> dict[str, Any]:
    validate_id(product_id, "product ID")
    manifest = _read_manifest(investigation_id)
    for record in manifest.get("products", []):
        if record.get("product_id") == product_id:
            return record
    raise ProductStorageError("Product was not found.", 404)


def product_path(investigation_id: str, product_id: str) -> Path:
    record = product_record(investigation_id, product_id)
    root = investigation_root(investigation_id)
    path = (root / str(record["relative_path"])).resolve()
    if root != path.parent or not path.is_file():
        raise ProductStorageError("Stored product is unavailable.", 404)
    return path


def list_products(investigation_id: str) -> dict[str, Any]:
    manifest = _read_manifest(investigation_id)
    return {"investigation_id": investigation_id, "products": manifest.get("products", []), "processing_status": manifest.get("processing_status")}


def update_product(investigation_id: str, product_id: str, **updates: Any) -> dict[str, Any]:
    with _manifest_lock(investigation_id):
        manifest = _read_manifest(investigation_id)
        record = product_record(investigation_id, product_id)
        record.update(updates)
        _write_manifest(investigation_id, manifest)
        return record


def update_investigation(investigation_id: str, **updates: Any) -> dict[str, Any]:
    with _manifest_lock(investigation_id):
        manifest = _read_manifest(investigation_id)
        manifest.update(updates)
        _write_manifest(investigation_id, manifest)
        return manifest


def load_manifest(investigation_id: str) -> dict[str, Any]:
    return _read_manifest(investigation_id)


def cleanup_expired(*, now: datetime | None = None, retention_days: int | None = None) -> list[str]:
    root = storage_root()
    if not root.exists():
        return []
    days = retention_days if retention_days is not None else int(os.environ.get(RETENTION_ENV, DEFAULT_RETENTION_DAYS))
    if days < 0:
        raise ValueError("retention_days must be non-negative")
    current = now or datetime.now(timezone.utc)
    removed: list[str] = []
    for child in root.iterdir():
        if not child.is_dir() or not SAFE_ID.fullmatch(child.name):
            continue
        try:
            manifest = _read_manifest(child.name)
            created = datetime.fromisoformat(str(manifest["created_at_utc"]).replace("Z", "+00:00"))
            if (current - created).total_seconds() > days * 86400:
                shutil.rmtree(child)
                removed.append(child.name)
        except (ProductStorageError, KeyError, ValueError, OSError):
            continue
    return removed
