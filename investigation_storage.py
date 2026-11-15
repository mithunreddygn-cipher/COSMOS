"""Durable investigation snapshots backed by the existing local records store."""
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any
from . import product_storage

def _path(investigation_id: str):
    return product_storage.investigation_root(investigation_id) / "investigation.json"

def _valid(payload: Any, investigation_id: str) -> bool:
    return isinstance(payload, dict) and payload.get("investigation_id") == investigation_id and isinstance(payload.get("result"), dict)

def save(payload: dict[str, Any]) -> dict[str, Any]:
    investigation_id = product_storage.validate_id(str(payload.get("investigation_id")), "investigation ID")
    now = datetime.now(timezone.utc).isoformat()
    record = dict(payload)
    record.setdefault("created_at_utc", now); record["updated_at_utc"] = now
    path = _path(investigation_id); temporary = path.with_name(f".investigation-{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    try: temporary.replace(path)
    except PermissionError:
        path.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8"); temporary.unlink(missing_ok=True)
    return record

def load(investigation_id: str) -> dict[str, Any]:
    product_storage.validate_id(investigation_id, "investigation ID")
    path = _path(investigation_id)
    if not path.is_file(): raise product_storage.ProductStorageError("Investigation was not found.", 404)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise product_storage.ProductStorageError("Investigation record is corrupted.", 500) from exc
    if not _valid(payload, investigation_id): raise product_storage.ProductStorageError("Investigation record is invalid.", 500)
    return payload

def recover() -> dict[str, dict[str, Any]]:
    root = product_storage.storage_root(); recovered: dict[str, dict[str, Any]] = {}
    if not root.exists(): return recovered
    for child in root.iterdir():
        if not child.is_dir() or not product_storage.SAFE_ID.fullmatch(child.name): continue
        try: payload = load(child.name)
        except product_storage.ProductStorageError: continue
        recovered[child.name] = payload
    return recovered
