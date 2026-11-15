"""Immutable report snapshots stored alongside an investigation."""
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any
from . import product_storage

def _root(inv: str):
    root = product_storage.investigation_root(inv) / "reports"; root.mkdir(exist_ok=True); return root
def _index(inv: str): return _root(inv) / "index.json"
def _load(inv: str):
    p=_index(inv)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
def _save(inv: str, items):
    p=_index(inv); tmp=p.with_suffix('.tmp'); tmp.write_text(json.dumps(items,indent=2),encoding='utf-8')
    try: tmp.replace(p)
    except PermissionError: p.write_text(tmp.read_text(encoding='utf-8'),encoding='utf-8'); tmp.unlink(missing_ok=True)
def save_report(inv: str, report: dict[str, Any], products: list[dict[str, Any]]|None=None) -> dict[str, Any]:
    product_storage.validate_id(inv,'investigation ID'); rid=uuid.uuid4().hex; now=datetime.now(timezone.utc).isoformat()
    meta={'report_id':rid,'investigation_id':inv,'generated_at_utc':now,'format':'json','schema_version':report.get('report_schema','cosmos-investigation-v1'),'source_product_ids':[p.get('product_id') for p in products or []],'source_product_hashes':[p.get('sha256') for p in products or []]}
    path=_root(inv)/f'{rid}.json'; path.write_text(json.dumps({'metadata':meta,'report':report},indent=2,default=str),encoding='utf-8'); items=_load(inv); items.append(meta); _save(inv,items); return meta
def list_reports(inv): product_storage.validate_id(inv,'investigation ID'); return _load(inv)
def load_report(inv,rid):
    product_storage.validate_id(inv,'investigation ID'); product_storage.validate_id(rid,'report ID'); p=_root(inv)/f'{rid}.json'
    if not p.is_file(): raise product_storage.ProductStorageError('Report was not found.',404)
    return json.loads(p.read_text(encoding='utf-8'))
