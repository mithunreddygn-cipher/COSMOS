"""COSMOS research interface for uploaded FITS and IRSA SIA2 products."""
from __future__ import annotations

import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from ingest.irsa_adapter import manifest_from_sia_rows
from ingest.irsa_client import (
    IrsaError, SPHEREX_COLLECTIONS, build_cutout_url, build_sia2_query_url,
    download_product, query_sia2,
)
from ingest.upload_handler import inspect_paths, write_manifest
from science.fits_processing import fits_preview
from science.pipeline import run_fits_pipeline
from ui.mission_control import (
    apply_mission_control_theme,
    render_investigation_results,
    render_mission_control,
    render_scientific_report,
    render_source_explorer,
)


@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def _cached_sia2_query(url: str):
    return query_sia2(url)


@st.cache_data(ttl=86400, max_entries=3, show_spinner=False)
def _cached_product_download(url: str):
    return download_product(url, max_bytes=8_000_000)


st.set_page_config(page_title="COSMOS | Astronomical Investigation", page_icon="✦", layout="wide")
apply_mission_control_theme()
st.markdown('<div class="cosmos-eyebrow">SPHEREx · Evidence-driven astronomy</div>', unsafe_allow_html=True)
st.title("COSMOS")
st.caption("Measurements · Uncertainty · Provenance · Reproducible investigation")

for key, default in (("cosmos_upload_fingerprint", None), ("cosmos_upload_tempdir", None), ("cosmos_upload_products", []), ("cosmos_manifest", None), ("cosmos_analysis", None), ("cosmos_previews", []), ("cosmos_irsa_rows", []), ("cosmos_irsa_query", None), ("cosmos_irsa_error", None)):
    if key not in st.session_state:
        st.session_state[key] = default

mission_tab, explore_tab, source_tab, investigation_tab, report_tab = st.tabs([
    "Mission Control", "Explore Observations", "Source Explorer", "Investigation Results", "Scientific Reports",
])

with mission_tab:
    if st.button("Run synthetic three-epoch demonstration", type="primary"):
        demo_root = Path(__file__).parent / "sample_data" / "synthetic_demo"
        demo_paths = sorted(demo_root.glob("cosmos_synthetic_epoch_*.fits"))
        if len(demo_paths) != 3:
            st.error(f"Expected three bundled synthetic FITS fixtures; found {len(demo_paths)}.")
        else:
            prior_tempdir = st.session_state.cosmos_upload_tempdir
            if prior_tempdir is not None:
                prior_tempdir.cleanup()
                st.session_state.cosmos_upload_tempdir = None
            with st.spinner("Running the standard FITS ingestion and scientific investigation pipeline on synthetic fixtures…"):
                manifest = inspect_paths(demo_paths)
                analysis = run_fits_pipeline(manifest, [str(path) for path in demo_paths])
                previews = []
                for product_index, product in enumerate(analysis.get("fits_processing", {}).get("products", []), start=1):
                    if not product.get("result", {}).get("metadata"):
                        continue
                    try:
                        previews.append({
                            "file": Path(product["path"]).name,
                            "label": f"{product_index} · {Path(product['path']).name}",
                            "metadata": product["result"]["metadata"],
                            **fits_preview(product["path"]),
                        })
                    except (ValueError, OSError) as exc:
                        analysis.setdefault("limitations", []).append(
                            f"Image preview unavailable for {Path(product['path']).name}: {exc}"
                        )
            st.session_state.cosmos_upload_fingerprint = None
            st.session_state.cosmos_manifest = analysis.get("enriched_manifest", manifest)
            st.session_state.cosmos_analysis = analysis
            st.session_state.cosmos_previews = previews[:8]
            st.session_state.cosmos_upload_products = [
                {"path": item["path"], "filename": Path(item["path"]).name, "metadata": item["result"].get("metadata", {})}
                for item in analysis.get("fits_processing", {}).get("products", [])
                if item["result"].get("metadata")
            ]
            st.session_state.cosmos_irsa_query = None
            st.session_state.cosmos_irsa_rows = []
            st.session_state.cosmos_irsa_error = None
            st.success("Synthetic investigation completed by the same pipeline used for uploaded FITS observations.")
    render_mission_control(st.session_state.cosmos_manifest, st.session_state.cosmos_analysis)
    st.caption("The bundled demonstration is synthetic software validation, not real SPHEREx observation or discovery evidence.")

with explore_tab:
    st.subheader("Observation inventory")
    manifest = st.session_state.cosmos_manifest
    if not manifest:
        st.info("Upload files in Explore Observations or submit an IRSA query to populate the observation inventory.")
    else:
        quality = manifest.get("quality_summary", {})
        cols = st.columns(4)
        cols[0].metric("Files", quality.get("file_count", 0))
        cols[1].metric("Products", quality.get("product_count", 0))
        cols[2].metric("Observations", quality.get("observation_count", len(manifest.get("observations", []))))
        cols[3].metric("Distinct epochs", quality.get("distinct_epoch_count", len(manifest.get("epochs", []))))
        st.write("Dataset status:", manifest.get("analysis_status", "unknown"))
        st.dataframe(manifest.get("observations", []), use_container_width=True, hide_index=True)
        st.subheader("File provenance")
        st.dataframe([{key: row.get(key) for key in ("filename", "format", "status", "size_bytes", "sha256", "product_id", "missing_information")} for row in manifest.get("files", [])], use_container_width=True, hide_index=True)
        if manifest.get("missing_information"):
            with st.expander("Missing information and limitations"):
                for item in manifest["missing_information"]:
                    st.write(f"• {item}")

with explore_tab:
    st.subheader("Load astronomical observations")
    upload_tab, irsa_tab = st.tabs(["Upload local files", "Search and retrieve from IRSA"])
    with upload_tab:
        st.write("Accepted: FITS, CSV, JSON, ECSV, VOTable, plus reference-only PNG/JPEG/PDF. Image processing uses recognized 2-D IMAGE/SCI/SCIENCE HDUs only.")
        uploads = st.file_uploader("Select data products", accept_multiple_files=True, type=["fits", "fit", "fts", "csv", "json", "ecsv", "vot", "votable", "png", "jpg", "jpeg", "pdf"])
        if uploads:
            fingerprint = hashlib.sha256()
            for upload in uploads:
                fingerprint.update(Path(upload.name).name.encode("utf-8"))
                fingerprint.update(hashlib.sha256(upload.getbuffer()).digest())
            fingerprint_value = fingerprint.hexdigest()
            if fingerprint_value != st.session_state.cosmos_upload_fingerprint:
                with st.spinner("Inspecting files, measuring FITS sources, and running quality-aware analysis…"):
                    prior_tempdir = st.session_state.cosmos_upload_tempdir
                    if prior_tempdir is not None:
                        prior_tempdir.cleanup()
                    tempdir = tempfile.TemporaryDirectory(prefix="cosmos-upload-")
                    st.session_state.cosmos_upload_tempdir = tempdir
                    paths = []
                    for upload_index, upload in enumerate(uploads, start=1):
                        product_dir = Path(tempdir.name, f"{upload_index:04d}")
                        product_dir.mkdir()
                        path = product_dir / Path(upload.name).name
                        with path.open("wb") as handle:
                            handle.write(upload.getbuffer())
                        paths.append(path)
                    manifest = inspect_paths(paths)
                    analysis = run_fits_pipeline(manifest, [str(path) for path in paths])
                    previews = []
                    for product_index, product in enumerate(analysis.get("fits_processing", {}).get("products", []), start=1):
                        if product["result"].get("metadata"):
                            try:
                                preview = fits_preview(product["path"])
                                previews.append({"file": Path(product["path"]).name, "label": f"{product_index} · {Path(product['path']).name}", "metadata": product["result"].get("metadata", {}), **preview})
                            except (ValueError, OSError) as exc:
                                analysis.setdefault("limitations", []).append(f"Image preview unavailable for {Path(product['path']).name}: {exc}")
                st.session_state.cosmos_upload_fingerprint = fingerprint_value
                st.session_state.cosmos_manifest = analysis.get("enriched_manifest", manifest)
                st.session_state.cosmos_analysis = analysis
                st.session_state.cosmos_previews = previews[:8]
                st.session_state.cosmos_upload_products = [{"path": item["path"], "filename": Path(item["path"]).name, "metadata": item["result"].get("metadata", {})} for item in analysis.get("fits_processing", {}).get("products", []) if item["result"].get("metadata")]
                st.rerun()
            st.success("Upload processed. Review Mission Control, Explore Observations, Source Explorer, Investigation Results, and Scientific Reports.")
        if st.session_state.cosmos_previews:
            st.markdown("#### Loaded image products")
            previews = st.session_state.cosmos_previews
            names = [row.get("label", row["file"]) for row in previews]
            selected_name = st.selectbox("Image product", names, key="upload_preview_selection")
            selected = next(item for item in previews if item.get("label", item["file"]) == selected_name)
            selected_file = selected["file"]
            selected_obs_id = selected.get("metadata", {}).get("observation_id")
            st.caption(f"Extension {selected['extension']} · original dimensions {selected['original_shape']} · preview stride {selected['stride']} pixels · display stretch only")
            metadata = selected.get("metadata", {})
            st.write({"observation_id": metadata.get("observation_id"), "timestamp": metadata.get("timestamp"), "exposure_time_seconds": metadata.get("exposure_time_seconds"), "detector": metadata.get("detector"), "frame_center_ra_deg": metadata.get("frame_center_ra"), "frame_center_dec_deg": metadata.get("frame_center_dec"), "field_of_view_arcmin": metadata.get("fov_arcmin"), "coordinate_frame": metadata.get("coordinate_frame"), "pixel_scales_arcsec": metadata.get("pixel_scales_arcsec"), "wcs_present": metadata.get("wcs_present"), "wcs_valid": metadata.get("wcs_valid")})
            contrast = st.slider("Display contrast upper bound", min_value=0.2, max_value=1.0, value=1.0, step=0.05, key="display_contrast")
            try:
                import plotly.graph_objects as go
                figure = go.Figure(go.Heatmap(z=selected["image"], colorscale="Gray", zmin=0, zmax=contrast, colorbar={"title": "Display stretch"}))
                figure.update_layout(height=620, xaxis_title="Preview pixel", yaxis_title="Preview pixel", margin={"l": 20, "r": 20, "t": 20, "b": 20})
                source_rows = [row for row in (st.session_state.cosmos_analysis or {}).get("fits_processing", {}).get("measurements", []) if row.get("file") == selected_file and (selected_obs_id is None or row.get("observation_id") == selected_obs_id)]
                if source_rows:
                    stride = selected["stride"]
                    figure.add_trace(go.Scatter(x=[row["x_pixel"] / stride for row in source_rows], y=[row["y_pixel"] / stride for row in source_rows], mode="markers", name="Measured sources", marker={"color": "red", "symbol": "circle-open", "size": 12}))
                st.plotly_chart(figure, use_container_width=True)
            except ImportError:
                st.image(selected["image"], clamp=True, caption="Bounded normalized preview; scientific arrays remain unmodified.")
            sources = [row for row in (st.session_state.cosmos_analysis or {}).get("fits_processing", {}).get("measurements", []) if row.get("file") == selected_file and (selected_obs_id is None or row.get("observation_id") == selected_obs_id)]
            st.dataframe(sources, use_container_width=True, hide_index=True)
            if len(previews) >= 2:
                st.markdown("#### Compare two observation previews")
                compare_names = st.multiselect("Choose image products", names, max_selections=2, key="compare_image_products")
                if len(compare_names) == 2:
                    first = next(item for item in previews if item.get("label", item["file"]) == compare_names[0])
                    second = next(item for item in previews if item.get("label", item["file"]) == compare_names[1])
                    first_obs, second_obs = first.get("metadata", {}).get("observation_id"), second.get("metadata", {}).get("observation_id")
                    compatibilities = (st.session_state.cosmos_analysis or {}).get("compatibility_assessments", [])
                    pair = next((item for item in compatibilities if {item.get("first"), item.get("second")} == {first_obs, second_obs}), None)
                    if pair:
                        st.write(f"Temporal brightness gate: **{pair['result']['status']}** — {pair['result']['explanation']}")
                    else:
                        st.write("Temporal brightness gate: **UNTESTABLE** — no evaluated observation pair is available.")
                    try:
                        from plotly.subplots import make_subplots
                        import plotly.graph_objects as go
                        figure = make_subplots(rows=1, cols=2, subplot_titles=compare_names)
                        figure.add_trace(go.Heatmap(z=first["image"], colorscale="Gray", zmin=0, zmax=1), row=1, col=1)
                        figure.add_trace(go.Heatmap(z=second["image"], colorscale="Gray", zmin=0, zmax=1), row=1, col=2)
                        figure.update_layout(height=500, showlegend=False)
                        st.plotly_chart(figure, use_container_width=True)
                    except ImportError:
                        st.info("Install the optional science dependencies to show side-by-side Plotly views.")
                    st.caption("Side-by-side preview is visual only. Quantitative image addition/subtraction also requires registered WCS, PSF/background matching, compatible quality masks, and variance propagation.")

    with irsa_tab:
        st.caption("Searches current IRSA SIA2 SPHEREx collections. A successful empty result differs from network/service/query failure.")
        with st.form("irsa-sia2-query"):
            col1, col2, col3 = st.columns(3)
            ra = col1.number_input("Right ascension (degrees)", min_value=0.0, max_value=359.999999, value=269.452075, format="%.6f")
            dec = col2.number_input("Declination (degrees)", min_value=-90.0, max_value=90.0, value=4.693391, format="%.6f")
            radius = col3.number_input("Search radius (degrees)", min_value=0.001, max_value=5.0, value=0.1, format="%.3f")
            collection_label = st.selectbox("Searchable collection", list(SPHEREX_COLLECTIONS.values()), index=list(SPHEREX_COLLECTIONS.values()).index("spherex_qr3"))
            target = st.text_input("Target label (optional)", value="Barnard's Star")
            submitted = st.form_submit_button("Query IRSA SIA2")
        if submitted:
            if st.session_state.cosmos_upload_tempdir is not None:
                st.session_state.cosmos_upload_tempdir.cleanup()
                st.session_state.cosmos_upload_tempdir = None
            st.session_state.cosmos_upload_products = []
            st.session_state.cosmos_upload_fingerprint = None
            url = build_sia2_query_url(ra, dec, radius, collection_label, target=target or None)
            st.session_state.cosmos_irsa_query = {"url": url, "ra_deg": ra, "dec_deg": dec, "radius_deg": radius, "collection": collection_label, "target": target or None}
            st.session_state.cosmos_irsa_error = None
            try:
                with st.spinner("Waiting for the bounded IRSA SIA2 query…"):
                    st.session_state.cosmos_irsa_rows = _cached_sia2_query(url)
                st.session_state.cosmos_manifest = manifest_from_sia_rows(st.session_state.cosmos_irsa_rows, ra_deg=ra, dec_deg=dec, collection=collection_label, query_url=url)
                st.session_state.cosmos_analysis = None
                st.session_state.cosmos_previews = []
            except IrsaError as exc:
                st.session_state.cosmos_irsa_rows = []
                st.session_state.cosmos_irsa_error = {"status": exc.status, "message": str(exc), "query_url": url}
            st.rerun()
        error = st.session_state.cosmos_irsa_error
        if error:
            st.error(f"{error['status']}: {error['message']}")
            st.code(error["query_url"])
        elif st.session_state.cosmos_irsa_query:
            rows = st.session_state.cosmos_irsa_rows
            st.code(st.session_state.cosmos_irsa_query["url"])
            if not rows:
                st.info("NO_OBSERVATIONS_FOUND: IRSA returned a valid empty SIA2 result for this query.")
            else:
                st.success(f"{len(rows)} archive product rows returned. Select at most three small cutouts to download.")
                def product_id(row, index):
                    return next((value for key, value in row.items() if key.lower() in {"obs_publisher_did", "product_id", "id", "access_url", "accessurl"} and value), f"row-{index + 1}")
                product_rows = {}
                for index, row in enumerate(rows):
                    base_id = product_id(row, index)
                    identifier = base_id if base_id not in product_rows else f"{base_id}#{index + 1}"
                    product_rows[identifier] = row
                st.dataframe([{"product_id": key, **{name: row.get(name) for name in ("obs_id", "obsid", "t_min", "t_max", "em_min", "em_max", "access_format", "access_estsize")}} for key, row in product_rows.items()], use_container_width=True, hide_index=True)
                with st.form("download-selected-products"):
                    selected_products = st.multiselect("Product identifiers", list(product_rows), max_selections=3)
                    cutout_size = st.number_input("Cutout side (degrees, maximum 0.2)", min_value=0.005, max_value=0.2, value=0.05, step=0.005)
                    download_submitted = st.form_submit_button("Download selected FITS cutouts and analyze")
                if download_submitted:
                    query = st.session_state.cosmos_irsa_query
                    downloaded_paths = []
                    download_provenance = {}
                    download_errors = []
                    with st.spinner("Downloading bounded cutouts and processing image arrays…"):
                        with tempfile.TemporaryDirectory(prefix="cosmos-irsa-") as tmp:
                            for index, identifier in enumerate(selected_products):
                                row = product_rows[identifier]
                                access_url = next((value for key, value in row.items() if key.lower() in {"access_url", "accessurl"} and value), None)
                                if not access_url:
                                    download_errors.append(f"{identifier}: result has no access_url.")
                                    continue
                                try:
                                    cutout_url = build_cutout_url(access_url, query["ra_deg"], query["dec_deg"], cutout_size)
                                    body = _cached_product_download(cutout_url)
                                    source_filename = Path(urlparse(access_url).path).name
                                    if not source_filename.lower().endswith((".fits", ".fit", ".fts")):
                                        source_filename = f"{hashlib.sha256(identifier.encode()).hexdigest()[:10]}.fits"
                                    product_dir = Path(tmp, f"{index + 1:04d}")
                                    product_dir.mkdir()
                                    path = product_dir / source_filename
                                    path.write_bytes(body)
                                    downloaded_paths.append(path)
                                    digest = hashlib.sha256(body).hexdigest()
                                    download_provenance[digest] = {"archive_product_id": identifier.split("#", 1)[0], "access_url": access_url, "cutout_url": cutout_url, "sia2_row": row, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(), "downloaded_size_bytes": len(body), "download_sha256": digest}
                                except (IrsaError, ValueError, OSError) as exc:
                                    download_errors.append(f"{identifier}: {type(exc).__name__}: {exc}")
                            if downloaded_paths:
                                product_manifest = inspect_paths(downloaded_paths)
                                analysis = run_fits_pipeline(product_manifest, [str(path) for path in downloaded_paths])
                                previews = []
                                previous_tempdir = st.session_state.cosmos_upload_tempdir
                                if previous_tempdir is not None:
                                    previous_tempdir.cleanup()
                                retained_tempdir = tempfile.TemporaryDirectory(prefix="cosmos-session-products-")
                                st.session_state.cosmos_upload_tempdir = retained_tempdir
                                retained_products = []
                                for product in analysis.get("fits_processing", {}).get("products", []):
                                    try:
                                        previews.append({"file": Path(product["path"]).name, "metadata": product["result"].get("metadata", {}), **fits_preview(product["path"])})
                                    except (ValueError, OSError) as exc:
                                        analysis.setdefault("limitations", []).append(f"Preview unavailable: {exc}")
                                    retained_dir = Path(retained_tempdir.name, str(len(retained_products) + 1))
                                    retained_dir.mkdir()
                                    retained_path = retained_dir / Path(product["path"]).name
                                    import shutil
                                    shutil.copyfile(product["path"], retained_path)
                                    retained_products.append({"path": str(retained_path), "filename": retained_path.name, "metadata": product["result"].get("metadata", {})})
                                st.session_state.cosmos_upload_products = retained_products
                            else:
                                analysis = None
                                product_manifest = None
                                previews = []
                    if product_manifest:
                        product_manifest["source"] = "irsa_download"
                        product_manifest["target"] = {"name": query.get("target"), "ra": query["ra_deg"], "dec": query["dec_deg"]}
                        product_manifest["query"] = {**query, "downloaded_product_ids": selected_products, "cutout_size_deg": cutout_size, "executed_at_utc": datetime.now(timezone.utc).isoformat()}
                        for item in product_manifest["files"]:
                            provenance = download_provenance.get(item.get("sha256"), {})
                            item.update(provenance)
                            if provenance.get("archive_product_id"):
                                item["product_id"] = provenance["archive_product_id"]
                        for observation in product_manifest["observations"]:
                            for product in observation.get("products", []):
                                product.update(download_provenance.get(product.get("sha256"), {}))
                                if product.get("archive_product_id"):
                                    product["product_id"] = product["archive_product_id"]
                        analysis["enriched_manifest"]["source"] = "irsa_download"
                        analysis["enriched_manifest"]["target"] = product_manifest["target"]
                        analysis["enriched_manifest"]["query"] = product_manifest["query"]
                        from report.report_builder import build_report
                        analysis["report"] = build_report(analysis["enriched_manifest"], analysis)
                        st.session_state.cosmos_manifest = analysis["enriched_manifest"]
                        st.session_state.cosmos_analysis = analysis
                        st.session_state.cosmos_previews = previews
                    for message in download_errors:
                        st.error(f"DOWNLOAD_FAILED: {message}")
                    if analysis:
                        st.success("Selected products processed through the existing pipeline. Review Mission Control and the investigation screens.")
                        st.rerun()

with source_tab:
    render_source_explorer(st.session_state.cosmos_analysis)

with investigation_tab:
    analysis = st.session_state.cosmos_analysis
    if not analysis:
        render_investigation_results(None)
    else:
        render_investigation_results(analysis)
        st.subheader("Image comparison and arithmetic gate")
        manifest = st.session_state.cosmos_manifest or {}
        observations = manifest.get("observations", [])
        if len(observations) >= 2:
            labels = {str(item.get("observation_id") or item.get("file")): item for item in observations}
            chosen = st.multiselect("Choose two epochs to evaluate", list(labels), max_selections=2)
            operation = st.selectbox("Image operation", ["addition", "subtraction"])
            run_operation = st.button("Check compatibility and run image operation", disabled=len(chosen) != 2)
            if len(chosen) == 2 and run_operation:
                from gate.compatibility_engine import check_image_operation_compatibility
                from science.fits_processing import load_registered_image_inputs
                from science.image_operations import execute_image_operation
                path_by_observation = {str(item.get("metadata", {}).get("observation_id")): item["path"] for item in st.session_state.cosmos_upload_products}
                try:
                    first_inputs = load_registered_image_inputs(path_by_observation[chosen[0]])
                    second_inputs = load_registered_image_inputs(path_by_observation[chosen[1]])
                    first_record, second_record = dict(labels[chosen[0]]), dict(labels[chosen[1]])
                    first_record.update(first_inputs["metadata"])
                    second_record.update(second_inputs["metadata"])
                    psf_match = bool(first_inputs["psf_signature"] and first_inputs["psf_signature"] == second_inputs["psf_signature"])
                    background_match = bool(first_inputs["background_method"] == second_inputs["background_method"] and first_inputs["background_rms_native"] > 0 and second_inputs["background_rms_native"] > 0)
                    common_mask = first_inputs["flags_interpreted"] and second_inputs["flags_interpreted"] and first_inputs["mask"].shape == second_inputs["mask"].shape and bool((first_inputs["mask"] == second_inputs["mask"]).all())
                    variance_available = first_inputs["variance"] is not None and second_inputs["variance"] is not None
                    for record in (first_record, second_record):
                        record["psf_matched"] = psf_match
                        record["background_matched"] = background_match
                        record["quality_mask_compatible"] = common_mask
                        record["variance_available"] = variance_available
                    gate_result = check_image_operation_compatibility(first_record, second_record, operation).to_dict()
                except (KeyError, ValueError, OSError) as exc:
                    gate_result = {"operation": f"image_{operation}", "status": "UNTESTABLE", "allowed": False, "checks": [], "explanation": f"The selected products could not provide registered operation inputs: {exc}"}
                st.json(gate_result)
                if gate_result["allowed"]:
                    try:
                        operation_result = execute_image_operation(first_inputs["image"], second_inputs["image"], operation, compatibility=gate_result, first_variance=first_inputs["variance"], second_variance=second_inputs["variance"], first_mask=first_inputs["mask"], second_mask=second_inputs["mask"])
                        stride = max(1, int(max(operation_result["image"].shape) / 512))
                        st.write(f"{operation.title()} completed on {operation_result['pixels_used']:,} compatible pixels; independent variances were propagated.")
                        import plotly.graph_objects as go
                        figure = go.Figure(go.Heatmap(z=operation_result["image"][::stride, ::stride], colorscale="RdBu", colorbar={"title": "Background-subtracted signal"}))
                        figure.update_layout(height=520, title=f"Gate-authorized image {operation}")
                        st.plotly_chart(figure, use_container_width=True)
                    except (ValueError, ImportError) as exc:
                        st.error(f"IMAGE_OPERATION_FAILED: {exc}")
                else:
                    st.caption("No pixel operation was executed. Review the gate reasons above; unverified alignment, PSF/background, quality-mask, or variance compatibility blocks arithmetic.")
            elif len(chosen) == 2:
                st.caption("Select Check compatibility and run image operation to inspect product arrays and apply the gate. No operation runs in response to metadata selection alone.")
        else:
            st.caption("Image arithmetic needs at least two observations and the complete operation gate.")
        st.subheader("Analysis stages")
        st.dataframe(analysis.get("timeline", []), use_container_width=True, hide_index=True)

with report_tab:
    analysis = st.session_state.cosmos_analysis
    manifest = st.session_state.cosmos_manifest
    render_scientific_report(manifest, analysis)
    if analysis and manifest:
        stem = str(manifest.get("dataset_id") or "cosmos-investigation")
        if st.button("Save manifest to records/manifests"):
            destination = Path("records/manifests") / f"{stem}.json"
            write_manifest(manifest, destination)
            st.success(f"Manifest saved to {destination}")
