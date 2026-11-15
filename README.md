# COSMOS

**The Engine That Investigates What Remains Unexplained.**

COSMOS is a modular astronomical investigation application. It ingests uploads and IRSA SIA2 products, preserves provenance, measures supported FITS image products, applies quality and compatibility gates, runs conservative screening algorithms, and creates reproducible reports.

## Install and run on Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[science,test]"
.\.venv\Scripts\python.exe -m streamlit run main.py
```

Run offline automated tests with:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

## Implemented workflow

- Supported file identification, FITS inspection, chunked SHA-256 provenance, duplicate detection, partial-success manifests, and missing-information reporting.
- IRSA SIA2 cone query, product selection, bounded cutout downloads, query/download caching, and a reproducible command-line audit. Network, service, query, download, and valid-empty outcomes remain distinct.
- Recognized 2-D FITS image extraction, conservative Level 2 quality-flag masking, background estimation, source detection, fixed-aperture photometry, VARIANCE-based uncertainty estimates, WCS coordinates, and bounded Plotly previews.
- Per-source image-plane morphology from Photutils segmentation moments, reported as uncalibrated ellipticity, elongation, orientation, and axis scales; no PSF deconvolution or point/extended-source classification is implied.
- Explicit CSV/ECSV/VOTable measurements can enter the same scientific pipeline when canonical measurement columns are present.
- Compatible single-source light curves can be screened for periodicity with a weighted Lomb-Scargle periodogram; the result remains a candidate and carries its period search range, peak power, false-alarm estimate, and observation evidence.
- Measurement-aware quality findings, data-driven temporal/spatial compatibility checks, conservative multi-observation source tracks, temporal/spectral/spatial screening, persistence and variability classifications, proper-motion candidates, conservative hypothesis evidence, and JSON/CSV/HTML report exports.
- Streamlit Mission Control with observation timeline, pipeline event log, compatibility and quality status, sky-coordinate source explorer, investigation results, and reproducible report downloads.

The detection algorithms are screening methods, not a validated discovery pipeline. No candidate is a discovery claim. The Compatibility Gate blocks image arithmetic when registration, PSF/background matching, masks, or uncertainty propagation are not established.

## Mission Control

Launch the Streamlit application from the repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run main.py
```

The navigation contains **Mission Control**, **Explore Observations**, **Source Explorer**, **Investigation Results**, and **Scientific Reports**. Explore Observations retains local FITS upload and bounded IRSA query/download flows. The Mission Control page offers a bundled three-epoch synthetic demonstration; it calls the same `inspect_paths` and `run_fits_pipeline` path as local FITS uploads. Counts and classifications are read from pipeline results, and unavailable data is shown as unavailable rather than filled with sample values.

The observation timeline uses reported IDs/timestamps and provides record details; missing times remain missing. The source plot uses only measurements marked WCS-valid with RA/Dec and a coordinate frame. It does not convert detector pixels into sky coordinates. Investigation Results separates temporal, spectral, spatial, proper-motion, and hypothesis evidence. Scientific Reports displays the generated report and offers its existing JSON, CSV, HTML, and manifest downloads.

The synthetic demonstration is explicitly labeled as synthetic. It is not a real SPHEREx observation or discovery. The interface does not add telescope telemetry, generate scientific measurements, or replace `UNTESTABLE` results with positive or negative conclusions. Browser styling and optional Plotly visualizations do not change analysis values.

## Input formats and analysis eligibility

COSMOS processes recognized 2-D FITS science-image products and their supported calibration inputs. CSV, ECSV, and VOTable tables are parsed and can contribute rows when they use the pipeline's canonical measurement fields; use `wavelength_um`, `ra_deg`, `dec_deg`, explicit coordinate frame, observation/source IDs, uncertainties, bandpass, and flux units. ECSV/VOTable column-unit metadata is retained during ingestion but is not yet automatically normalized by the analysis adapter; values therefore must already match the canonical units. Standalone FITS binary tables are not yet routed into the measurement pipeline. JSON is metadata/provenance input, and PNG/JPEG/PDF files are reference-only, not calibrated observations.

An image extension or recognized file suffix does not establish scientific calibration. Unsupported or incomplete data remain limited or untestable instead of being assigned invented units or measurements.

## FITS and SPHEREx limits

The inspector recognizes image, flags, variance, PSF/ePSF, zodiacal-light, and WCS-wavelength extension roles. The dedicated WCS-WAVE parser preserves the raw X, Y, and VALUES arrays, shapes, and dtypes in FITS processing results, and separately reports parsing and structural-validation status. A structurally valid table is not automatically a wavelength calibration: channel meanings, units, and coordinate mapping require an explicit `WcsWaveMappingSpec`.

The current interpretation layer supports only a documented identity mapping from `IMAGE_PIXEL` coordinates, explicit pixel origin, explicit channel meaning and units, and bilinear interpolation. Other coordinate transformations are rejected. Extrapolation is disabled by default; enabling it requires a declared supported method and documentation reference. No meaning is inferred for VALUES channels. `run_fits_pipeline` accepts an optional `wcs_wave_mapping_spec`; the Streamlit UI does not provide calibration-spec configuration.

`CWAVE` and `CBAND` are treated as wavelength/bandwidth calibration metadata, not as a complete instrument-response model. A valid `CWAVE`/`CBAND` map validates coverage and unit-bearing calibration information only; it does not establish that the full spectral response function is known or equivalent between observations. The compatibility gate distinguishes these levels and keeps `instrument_response_validation` separate from `wavelength_calibration_validation` and `bandwidth_calibration_validation`.

Official standalone Spectral WCS calibration FITS files are ingested as calibration inputs, not science observations. The inspected D5 product contains separate 2040×2040 `CWAVE` and `CBAND` image extensions plus a `WCS-WAVE` control-point table; both maps declare microns and detector/coordinate metadata. COSMOS associates a map with a science image only when detector and coordinate convention agree, its raw WCS-WAVE controls match exactly, the map values agree with both documented control-point channels, and the documented active-pixel translation is supported. The saved QR3 science header does not identify an authoritative calibration version, so this consistency check does not prove which calibration release produced that observation. WCS-WAVE remains a consistency/visualization aid, not the source of the calibrated map values. Official laboratory response CSVs are retained as representative curves only; they do not establish per-observation or per-pixel full response.

Source wavelength or bandwidth is assigned only from an explicitly unit-bearing map or validated WCS-WAVE interpretation when its value is uniform across the complete, valid source aperture. No centroid-only lookup is used. Even a validated wavelength map does not establish instrument-response compatibility. Spectral screening additionally requires at least five distinct wavelength samples, positive uncertainties, explicit source and observation IDs, and explicit response compatibility; samples are never combined across sources or observations.

The saved QR3 Level-2 D5 product by itself has a WCS-WAVE table with `DETCOORD=sky`, no column units, and no documented VALUES channel semantics; COSMOS preserves its raw values and does not use it alone as a wavelength calibration. With the separately supplied official D5 calibration FITS, map values and control points validate a wavelength/bandwidth association for this product, but not an authoritative calibration-version link or full instrument response. The measured source aperture spans non-uniform wavelength and bandwidth values, so no scalar source wavelength or bandwidth is assigned. This verifies only this product pairing, not general SPHEREx compatibility or source identification. Details and limits are in [docs/real_data_audit.md](docs/real_data_audit.md). Synthetic mapping fixtures establish software behavior only, not real SPHEREx calibration. PSF fitting/aperture correction, calibrated multi-product spectral assembly, WCS reprojection, proper-motion-aware matching, and product-specific systematics remain outstanding.

Partial or invalid aperture coverage is quantified but not corrected: if quality-flagged, invalid, or off-image area overlaps an aperture, the full-aperture flux is withheld and the measurement is marked `UNTESTABLE`. The valid-area partial sum is diagnostic only. Missing variance or uninterpreted flags produce a `LIMITED` measurement, which cannot enter quantitative temporal detection. PSF/ePSF availability does not count as PSF analysis.

Temporal brightness detection requires `RUNNABLE` compatibility. Matching wavelength intervals, detector labels, or calibration identifiers are not response evidence. Supply a per-observation `instrument_response_validation` record with independently validated response-curve equivalence (`status: VALIDATED_EQUIVALENT`, response curve/comparison/method/evidence identifiers), or a validated correction (`status: VALIDATED_CORRECTION`, correction/common-reference identifiers and `correction_applied: true`). CSV input may carry this object in an `instrument_response_validation_json` column. COSMOS consumes and reports this evidence; it does not generate or independently validate response curves. Without sufficient evidence, temporal brightness comparisons abstain.

The validated-equivalence record uses `response_curve_id`, a pair-shared `comparison_id`, `validation_method`, and `evidence_id`. The correction record uses `response_curve_id`, pair-shared `correction_id` and `common_reference`, `correction_applied: true`, `validation_method`, and `evidence_id`. These fields are provenance references, not response-curve values or calibration data generated by COSMOS.

## Multi-epoch investigations

`run_fits_pipeline` processes multiple FITS products together, orders observations by parsed timestamp (not input-file order), reports duplicate or untimed inputs, and associates detections only when WCS coordinates support an unambiguous match. Track IDs are internal association labels, not astronomical source identities. Temporal flux variability requires `RUNNABLE` compatibility and valid uncertainties. A transient candidate additionally requires explicit sensitivity-backed, compatible non-detections across multiple epochs; absent measurements remain unknown. Proper-motion candidates require at least three compatible positions with uncertainties and do not imply source identity, distance, or physical velocity. The returned `multi_epoch_investigation` and report contain the timeline, per-observation source counts, tracks, classifications, candidates, compatibility failures, and limitations.

Periodicity screening is a separate optional result within `detection_results`. It requires at least 10 distinct, valid epochs for one source, positive uncertainties, explicit common flux units and bandpass, and a RUNNABLE temporal Compatibility Gate. Its default search spans periods from twice the median cadence to one third of the observation baseline; a Baluev false-alarm estimate below 1% marks a `PERIODICITY_CANDIDATE`, not a discovery or a period measurement with established uncertainty. The threshold is per source and is not multiplicity-corrected. A caller may supply `periodicity_options` in the pipeline manifest to set `minimum_period_days`, `maximum_period_days`, or `false_alarm_threshold`; the actual range and thresholds are retained in the report. Processing is bounded to 10,000 epochs and 100,000 frequency samples per source. Irregular-sampling aliases, correlated noise, and instrumental systematics are not modeled. No real SPHEREx light curve currently validates this screen; the synthetic test establishes software behavior only.

## Scientific reporting
Generated JSON/HTML reports now preserve measurement algorithms and their limitations, observation-level calibration evidence, detector status and evidence counts, source measurements, compatibility results, hypotheses, and reproducibility inputs. Morphology values describe threshold-segmented image-plane shapes only; PSF and astrometric calibration are not applied.

## IRSA and Barnard's Star

See [docs/real_data_audit.md](docs/real_data_audit.md) for the sample audit procedure and report format. The staged SIA2 response contains three QR3 rows for two observation identifiers over about 4.07 minutes, with non-contiguous D3/D6 wavelength bounds. It does not establish the full archive history or astrometric precision. The live IRSA audit and Barnard's Star feasibility remain unverified.

See [BUILD_STATUS.md](BUILD_STATUS.md) and [docs/implementation_checklist.md](docs/implementation_checklist.md) for verified status and remaining work. The local FastAPI adapter exposes scientific investigations and the isolated external-data routes below; investigation history remains in-memory and is not durable.

## External scientific data: Planetary Computer

The React workspace includes a separate Microsoft Planetary Computer STAC catalogue for Earth-observation discovery. It supports collection search, spatial bounding-box and date-range search, paged item results, STAC item and asset inspection, a catalogue-linked rendered-image preview, and explicit bounded asset downloads.

Install the optional API dependencies and run the local API and frontend in separate PowerShell windows:

```powershell
python -m pip install -e ".[api]"
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Set `VITE_API_BASE_URL` when the API is not at `http://127.0.0.1:8000`. The FastAPI route prefix is `/api/v1/external/planetary-computer/`; OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

Search bounding boxes use `west,south,east,north` longitude/latitude coordinates. Date filters require both dates or neither. Results and asset metadata preserve the STAC item/collection IDs, timestamps, geographic extents, asset references, licence/attribution, and retrieval time. Asset previews and downloads are proxied through bounded Python endpoints; signed asset URLs are not shown in the UI. Downloads are explicit and capped at 100 MiB (previews at 15 MiB).

Planetary Computer results are external environmental observations, not astronomical measurements. They are never uploaded to or combined by the SPHEREx scientific engine, and COSMOS does not infer environmental correlations. A preview is an actual remote STAC asset, not a COSMOS-calibrated astronomical image. The optional live STAC test can be enabled with `COSMOS_LIVE_PC_TEST=1`; normal tests use mocked responses and do not require the public service.
