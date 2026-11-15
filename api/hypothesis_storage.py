"""Investigation-scoped persistence for user-authored hypotheses."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import json
from . import product_storage

STATUSES = {"PROPOSED", "UNDER_INVESTIGATION", "SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "UNTESTABLE", "ARCHIVED"}

def _path(investigation_id: str):
    root = product_storage.investigation_root(investigation_id)
    return root / "hypotheses.json"

def _load(investigation_id: str) -> list[dict[str, Any]]:
    path = _path(investigation_id)
    if not path.exists(): return []
    return json.loads(path.read_text(encoding="utf-8"))

def _save(investigation_id: str, items: list[dict[str, Any]]) -> None:
    path = _path(investigation_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
    try:
        tmp.replace(path)
    except PermissionError:
        path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")
        tmp.unlink(missing_ok=True)

def list_hypotheses(investigation_id: str) -> list[dict[str, Any]]:
    product_storage.validate_id(investigation_id, "investigation ID")
    return _load(investigation_id)

def create_hypothesis(investigation_id: str, statement: str, rationale: str | None = None, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    product_storage.validate_id(investigation_id, "investigation ID")
    if not statement or not statement.strip(): raise product_storage.ProductStorageError("Hypothesis statement is required.", 422)
    now = datetime.now(timezone.utc).isoformat(); item = {"hypothesis_id": __import__('uuid').uuid4().hex, "investigation_id": investigation_id, "statement": statement.strip(), "rationale": rationale, "created_at": now, "updated_at": now, "origin": "USER", "status": "PROPOSED", "evidence": evidence or [], "unresolved_questions": [], "additional_evidence_requirements": []}
    items = _load(investigation_id); items.append(item); _save(investigation_id, items); return item

def get_hypothesis(investigation_id: str, hypothesis_id: str) -> dict[str, Any]:
    product_storage.validate_id(investigation_id, "investigation ID"); product_storage.validate_id(hypothesis_id, "hypothesis ID")
    for item in _load(investigation_id):
        if item["hypothesis_id"] == hypothesis_id: return item
    raise product_storage.ProductStorageError("Hypothesis was not found.", 404)

def update_hypothesis(investigation_id: str, hypothesis_id: str, **updates: Any) -> dict[str, Any]:
    items = _load(investigation_id); item = next((x for x in items if x.get("hypothesis_id") == hypothesis_id), None)
    if item is None: raise product_storage.ProductStorageError("Hypothesis was not found.", 404)
    allowed = {"statement", "rationale", "status", "notes", "unresolved_questions", "additional_evidence_requirements"}
    if "status" in updates and updates["status"] not in STATUSES: raise product_storage.ProductStorageError("Invalid hypothesis status.", 422)
    for key, value in updates.items():
        if key in allowed and value is not None: item[key] = value
    item["updated_at"] = datetime.now(timezone.utc).isoformat(); _save(investigation_id, items); return item

def associate_evidence(investigation_id: str, hypothesis_id: str, evidence_id: str, role: str = "INCONCLUSIVE") -> dict[str, Any]:
    if role not in {"SUPPORTING", "CONTRADICTORY", "INCONCLUSIVE", "UNRESOLVED"}: raise product_storage.ProductStorageError("Invalid evidence role.", 422)
    items = _load(investigation_id); item = next((x for x in items if x.get("hypothesis_id") == hypothesis_id), None)
    if item is None: raise product_storage.ProductStorageError("Hypothesis was not found.", 404)
    item.setdefault("evidence", [])
    if not any(e.get("evidence_id") == evidence_id for e in item["evidence"]): item["evidence"].append({"evidence_id": evidence_id, "role": role})
    item["updated_at"] = datetime.now(timezone.utc).isoformat(); _save(investigation_id, items); return item

def remove_evidence(investigation_id: str, hypothesis_id: str, evidence_id: str) -> dict[str, Any]:
    items = _load(investigation_id); item = next((x for x in items if x.get("hypothesis_id") == hypothesis_id), None)
    if item is None: raise product_storage.ProductStorageError("Hypothesis was not found.", 404)
    item["evidence"] = [e for e in item.get("evidence", []) if e.get("evidence_id") != evidence_id]; item["updated_at"] = datetime.now(timezone.utc).isoformat(); _save(investigation_id, items); return item

def compare(investigation_id: str, ids: list[str]) -> dict[str, Any]:
    selected = [get_hypothesis(investigation_id, item) for item in ids]; sets = [{e["evidence_id"] for e in h.get("evidence", [])} for h in selected]
    shared = sorted(set.intersection(*sets)) if sets else []
    return {"investigation_id": investigation_id, "hypotheses": selected, "shared_evidence": shared, "unique_evidence": {h["hypothesis_id"]: sorted(s-set.union(*(sets[:i]+sets[i+1:]))) for i,(h,s) in enumerate(zip(selected,sets))}}
