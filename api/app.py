"""Local FastAPI adapter; scientific calculations remain in the Python engine."""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from ingest.upload_handler import inspect_paths
from science.pipeline import run_fits_pipeline
from api import product_storage
from investigate.evidence_model import build_evidence_catalog, evidence_recommendations, hypothesis_catalog
from api import hypothesis_storage
from api import report_storage
from api import investigation_storage

try:  # FastAPI is an optional API runtime dependency.
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, PlainTextResponse, Response
    from fastapi.encoders import jsonable_encoder
except ImportError:  # pragma: no cover - exercised only without the optional extra.
    FastAPI = None  # type: ignore[assignment]

_INVESTIGATIONS: dict[str, dict[str, Any]] = {}


def _file_chunks(path: Path):
    with path.open("rb") as handle:
        while chunk := handle.read(product_storage.CHUNK_SIZE):
            yield chunk


def _investigation_payload(investigation_id: str) -> dict[str, Any] | None:
    payload = _INVESTIGATIONS.get(investigation_id)
    if payload is not None: return payload
    try:
        payload = investigation_storage.load(investigation_id)
    except product_storage.ProductStorageError:
        return None
    _INVESTIGATIONS[investigation_id] = payload
    return payload


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    investigation = result.get("multi_epoch_investigation") or {}
    detections = result.get("detection_results") or {}
    return {
        "status": result.get("status"),
        "observation_count": len((result.get("enriched_manifest") or {}).get("observations") or []),
        "source_measurement_count": len(result.get("measurements") or result.get("fits_processing", {}).get("measurements") or []),
        "analysis_statuses": {
            key: (value or {}).get("status") if isinstance(value, dict) else None
            for key, value in detections.items()
        },
        "track_count": len(investigation.get("tracks") or investigation.get("source_tracks") or []),
    }


def create_app() -> Any:
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install the API extra with: pip install -e \".[api]\"")
    from api.planetary_computer import router as planetary_computer_router
    _INVESTIGATIONS.update(investigation_storage.recover())

    app = FastAPI(title="COSMOS API", version="2.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(planetary_computer_router)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ready", "engine": "cosmos-python", "version": "2.0.0"}

    @app.post("/api/v1/investigations")
    async def create_investigation(files: list[UploadFile] = File(...)) -> dict[str, Any]:
        if not files or len(files) > 12:
            raise HTTPException(400, "Upload between 1 and 12 supported files.")
        investigation_id = uuid.uuid4().hex
        try:
            product_storage.create_investigation(investigation_id)
            product_records = []
            total = 0
            paths: list[Path] = []
            for uploaded in files:
                record = await product_storage.persist_upload(investigation_id, uploaded, max_bytes=50 * 1024 * 1024)
                total += int(record["size_bytes"])
                if total > 150 * 1024 * 1024:
                    raise product_storage.ProductStorageError("Upload exceeds the 150 MiB aggregate request limit.", 413)
                product_records.append(record)
                paths.append(product_storage.product_path(investigation_id, record["product_id"]))
            manifest = inspect_paths(paths)
            result = run_fits_pipeline(manifest, [str(path) for path in paths])
            for record, inspection in zip(product_records, manifest.get("inspection_results", [])):
                measurements = [item for item in (result.get("fits_processing", {}).get("measurements") or []) if item.get("file") == record["filename"]]
                product_storage.update_product(investigation_id, record["product_id"], metadata=inspection.get("metadata", {}), inspection_status=inspection.get("status"), missing_information=inspection.get("missing_information", []), measurements=measurements, processing_status=result.get("status"))
            product_storage.update_investigation(investigation_id, processing_status=result.get("status"), pipeline_status=result.get("status"))
            payload = {"investigation_id": investigation_id, "origin": "uploaded", "status": result.get("status"), "summary": _summary(result), "products": product_storage.list_products(investigation_id)["products"], "result": result}
            _INVESTIGATIONS[investigation_id] = investigation_storage.save(payload)
            return jsonable_encoder(_INVESTIGATIONS[investigation_id])
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.post("/api/v1/investigations/synthetic-demo")
    def synthetic_demo() -> dict[str, Any]:
        demo_root = Path(__file__).resolve().parents[1] / "sample_data" / "synthetic_demo"
        paths = sorted(demo_root.glob("cosmos_synthetic_epoch_*.fits"))
        if len(paths) != 3:
            raise HTTPException(503, "Bundled synthetic demonstration fixtures are unavailable.")
        investigation_id = str(uuid.uuid4())
        try:
            product_storage.create_investigation(investigation_id)
            product_records = [
                product_storage.persist_stream(investigation_id, path.name, _file_chunks(path))
                for path in paths
            ]
            stored_paths = [
                product_storage.product_path(investigation_id, record["product_id"])
                for record in product_records
            ]
            manifest = inspect_paths(stored_paths)
            manifest["source"] = "synthetic_demo"
            result = run_fits_pipeline(manifest, [str(path) for path in stored_paths])
            for record, inspection in zip(product_records, manifest.get("inspection_results", [])):
                measurements = [
                    item for item in (result.get("fits_processing", {}).get("measurements") or [])
                    if item.get("file") == record["filename"]
                ]
                product_storage.update_product(
                    investigation_id,
                    record["product_id"],
                    metadata=inspection.get("metadata", {}),
                    inspection_status=inspection.get("status"),
                    missing_information=inspection.get("missing_information", []),
                    measurements=measurements,
                    processing_status=result.get("status"),
                )
            product_storage.update_investigation(
                investigation_id,
                processing_status=result.get("status"),
                pipeline_status=result.get("status"),
            )
            payload = {
                "investigation_id": investigation_id,
                "origin": "synthetic",
                "status": result.get("status"),
                "summary": _summary(result),
                "products": product_storage.list_products(investigation_id)["products"],
                "result": result,
            }
            _INVESTIGATIONS[investigation_id] = investigation_storage.save(payload)
            return jsonable_encoder(_INVESTIGATIONS[investigation_id])
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}")
    def get_investigation(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        return jsonable_encoder(payload)

    @app.get("/api/v1/investigations/{investigation_id}/observations")
    def get_observations(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        manifest = payload["result"].get("enriched_manifest") or {}
        return jsonable_encoder({"observations": manifest.get("observations") or [], "provenance": manifest.get("provenance") or {}})

    @app.get("/api/v1/investigations/{investigation_id}/products")
    def products(investigation_id: str) -> dict[str, Any]:
        try:
            return jsonable_encoder(product_storage.list_products(investigation_id))
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/products/{product_id}")
    def product_detail(investigation_id: str, product_id: str) -> dict[str, Any]:
        try:
            return jsonable_encoder(product_storage.product_record(investigation_id, product_id))
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/products/{product_id}/manifest")
    def product_manifest(investigation_id: str, product_id: str) -> dict[str, Any]:
        """Return the persisted product manifest record without filesystem paths."""
        try:
            return jsonable_encoder(product_storage.product_record(investigation_id, product_id))
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/products/{product_id}/hdus")
    def product_hdus(investigation_id: str, product_id: str) -> dict[str, Any]:
        try:
            path = product_storage.product_path(investigation_id, product_id)
            from ingest.fits_audit import inspect_fits_product
            audit = inspect_fits_product(path)
            return jsonable_encoder({"investigation_id": investigation_id, "product_id": product_id, "filename": path.name, "status": audit.get("status"), "hdus": audit.get("hdus", []), "missing_information": audit.get("missing_information", [])})
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(422, f"FITS HDU inspection failed: {exc}") from exc

    @app.get("/api/v1/investigations/{investigation_id}/products/{product_id}/wcs")
    def product_wcs(investigation_id: str, product_id: str) -> dict[str, Any]:
        try:
            path = product_storage.product_path(investigation_id, product_id)
            from astropy.io import fits
            from astropy.wcs import WCS
            with fits.open(path, memmap=True, lazy_load_hdus=False) as hdus:
                image = next((hdu for hdu in hdus if str(hdu.header.get("EXTNAME", "")).upper() == "IMAGE"), hdus[0])
                header = image.header
                wcs = WCS(header).celestial
                keys = ("CTYPE1", "CTYPE2", "CRPIX1", "CRPIX2", "CRVAL1", "CRVAL2", "CD1_1", "CD1_2", "CD2_1", "CD2_2", "CDELT1", "CDELT2", "CUNIT1", "CUNIT2")
                return jsonable_encoder({"investigation_id": investigation_id, "product_id": product_id, "extension": header.get("EXTNAME", "PRIMARY"), "valid": bool(wcs.has_celestial), "header": {key: header[key] for key in keys if key in header}})
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(422, f"WCS metadata unavailable: {exc}") from exc

    def _preview_bytes(investigation_id: str, product_id: str, extension: str) -> tuple[bytes, dict[str, str]]:
        try:
            path = product_storage.product_path(investigation_id, product_id)
            from astropy.io import fits
            import numpy as np
            from PIL import Image
            from io import BytesIO
            with fits.open(path, memmap=True, lazy_load_hdus=False) as hdus:
                hdu = next((item for item in hdus if str(item.header.get("EXTNAME", "")).upper() == extension.upper()), None)
                if hdu is None or hdu.data is None or getattr(hdu.data, "ndim", 0) != 2:
                    raise HTTPException(422, f"HDU {extension} is not a 2-D image.")
                data = np.asarray(hdu.data, dtype=np.float64)
                finite = data[np.isfinite(data)]
                if finite.size == 0:
                    raise HTTPException(422, f"HDU {extension} contains no finite pixels.")
                low, high = np.percentile(finite, [1.0, 99.0])
                if not np.isfinite(low) or not np.isfinite(high) or high <= low:
                    low, high = float(np.min(finite)), float(np.max(finite))
                if high <= low:
                    scaled = np.zeros(data.shape, dtype=np.uint8)
                else:
                    scaled = np.clip((np.nan_to_num(data, nan=low, posinf=high, neginf=low) - low) / (high - low) * 255, 0, 255).astype(np.uint8)
                output = BytesIO()
                Image.fromarray(scaled, mode="L").save(output, format="PNG", optimize=True)
                headers = {"X-COSMOS-Investigation-ID": investigation_id, "X-COSMOS-Product-ID": product_id, "X-COSMOS-HDU": extension, "X-COSMOS-Display-Transform": "linear percentile stretch (1st-99th), display only", "X-COSMOS-Original-Dtype": str(hdu.data.dtype), "Cache-Control": "private, no-store"}
                return output.getvalue(), headers
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/products/{product_id}/preview")
    def product_preview(investigation_id: str, product_id: str, extension: str = "IMAGE") -> Any:
        body, headers = _preview_bytes(investigation_id, product_id, extension)
        return Response(body, media_type="image/png", headers=headers)

    @app.get("/api/v1/investigations/{investigation_id}/products/{product_id}/download")
    def product_download(investigation_id: str, product_id: str) -> Any:
        try:
            from fastapi.responses import FileResponse
            path = product_storage.product_path(investigation_id, product_id)
            record = product_storage.product_record(investigation_id, product_id)
            return FileResponse(path, media_type="application/fits", filename=record["original_filename"], headers={"Cache-Control": "private, no-store", "X-COSMOS-SHA256": record["sha256"]})
        except product_storage.ProductStorageError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/sources")
    def get_sources(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        result = payload["result"]
        investigation = result.get("multi_epoch_investigation") or {}
        return jsonable_encoder({"tracks": investigation.get("tracks") or investigation.get("source_tracks") or [], "measurements": result.get("measurements") or result.get("fits_processing", {}).get("measurements") or []})

    @app.get("/api/v1/investigations/{investigation_id}/results")
    def get_results(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        return jsonable_encoder(payload["result"])

    @app.get("/api/v1/investigations/{investigation_id}/evidence")
    def get_evidence(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        return jsonable_encoder({
            "investigation_id": investigation_id,
            "evidence": build_evidence_catalog(
                payload["result"],
                investigation_id,
                products=payload.get("products"),
            ),
        })

    @app.get("/api/v1/investigations/{investigation_id}/hypotheses")
    def get_hypotheses(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        return jsonable_encoder({"investigation_id": investigation_id, "hypotheses": hypothesis_catalog(payload["result"], investigation_id)})

    @app.get("/api/v1/investigations/{investigation_id}/evidence/recommendations")
    def get_evidence_recommendations(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        return jsonable_encoder({"investigation_id": investigation_id, "recommendations": evidence_recommendations(payload["result"])})

    @app.get("/api/v1/investigations/{investigation_id}/hypotheses/user")
    def list_user_hypotheses(investigation_id: str) -> dict[str, Any]:
        try: return jsonable_encoder({"investigation_id": investigation_id, "hypotheses": hypothesis_storage.list_hypotheses(investigation_id)})
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.post("/api/v1/investigations/{investigation_id}/hypotheses/user")
    async def create_user_hypothesis(investigation_id: str, body: dict[str, Any]) -> dict[str, Any]:
        try: return jsonable_encoder(hypothesis_storage.create_hypothesis(investigation_id, body.get("statement", ""), body.get("rationale"), body.get("evidence")))
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.patch("/api/v1/investigations/{investigation_id}/hypotheses/user/{hypothesis_id}")
    def update_user_hypothesis(investigation_id: str, hypothesis_id: str, body: dict[str, Any]) -> dict[str, Any]:
        try: return jsonable_encoder(hypothesis_storage.update_hypothesis(investigation_id, hypothesis_id, **body))
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.post("/api/v1/investigations/{investigation_id}/hypotheses/user/{hypothesis_id}/evidence")
    def attach_evidence(investigation_id: str, hypothesis_id: str, body: dict[str, Any]) -> dict[str, Any]:
        try: return jsonable_encoder(hypothesis_storage.associate_evidence(investigation_id, hypothesis_id, body.get("evidence_id", ""), body.get("role", "INCONCLUSIVE")))
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.delete("/api/v1/investigations/{investigation_id}/hypotheses/user/{hypothesis_id}/evidence/{evidence_id}")
    def detach_evidence(investigation_id: str, hypothesis_id: str, evidence_id: str) -> dict[str, Any]:
        try: return jsonable_encoder(hypothesis_storage.remove_evidence(investigation_id, hypothesis_id, evidence_id))
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.post("/api/v1/investigations/{investigation_id}/hypotheses/compare")
    def compare_hypotheses(investigation_id: str, body: dict[str, Any]) -> dict[str, Any]:
        try: return jsonable_encoder(hypothesis_storage.compare(investigation_id, body.get("hypothesis_ids", [])))
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.post("/api/v1/investigations/{investigation_id}/reports")
    def generate_report(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None: raise HTTPException(404, "Investigation not found.")
        try:
            meta = report_storage.save_report(investigation_id, payload["result"].get("report") or payload["result"], product_storage.list_products(investigation_id).get("products", []))
            return jsonable_encoder(meta)
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/reports")
    def list_reports(investigation_id: str) -> dict[str, Any]:
        try: return jsonable_encoder({"investigation_id": investigation_id, "reports": report_storage.list_reports(investigation_id)})
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/reports/{report_id}")
    def report_metadata(investigation_id: str, report_id: str) -> dict[str, Any]:
        try: return jsonable_encoder(report_storage.load_report(investigation_id, report_id)["metadata"])
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/reports/{report_id}/json")
    def stored_json_report(investigation_id: str, report_id: str) -> dict[str, Any]:
        try: return jsonable_encoder(report_storage.load_report(investigation_id, report_id)["report"])
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/reports/json")
    def get_json_report(investigation_id: str) -> dict[str, Any]:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        return jsonable_encoder(payload["result"].get("report") or payload["result"])

    @app.get("/api/v1/investigations/{investigation_id}/reports/{report_id}/html")
    def stored_html_report(investigation_id: str, report_id: str) -> Any:
        try:
            from report.report_builder import report_to_html
            return HTMLResponse(report_to_html(report_storage.load_report(investigation_id, report_id)["report"]))
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/reports/{report_id}/csv")
    def stored_csv_report(investigation_id: str, report_id: str) -> Any:
        try:
            from report.report_builder import report_to_csv
            return PlainTextResponse(report_to_csv(report_storage.load_report(investigation_id, report_id)["report"]), media_type="text/csv")
        except product_storage.ProductStorageError as exc: raise HTTPException(exc.status_code, str(exc)) from exc

    @app.get("/api/v1/investigations/{investigation_id}/reports/html")
    def get_html_report(investigation_id: str) -> Any:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        from report.report_builder import report_to_html
        return HTMLResponse(report_to_html(payload["result"].get("report") or payload["result"]))

    @app.get("/api/v1/investigations/{investigation_id}/reports/csv")
    def get_csv_report(investigation_id: str) -> Any:
        payload = _investigation_payload(investigation_id)
        if payload is None:
            raise HTTPException(404, "Investigation not found.")
        from report.report_builder import report_to_csv
        return PlainTextResponse(report_to_csv(payload["result"].get("report") or payload["result"]), media_type="text/csv")

    return app


app = create_app() if FastAPI is not None else None
