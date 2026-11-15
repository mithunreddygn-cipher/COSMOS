# Stitch design audit

## Scope and method

This is a read-only comparison of the two extracted Stitch exports:

- `stitch-handoff/export 1/stitch_cosmos_astronomical_investigation_platform`
- `stitch-handoff/export 2/stitch_cosmos_astronomical_investigation_platform`

Each screen directory contains a `code.html` mockup and usually a `screen.png` render. The HTML is design output, not a functional COSMOS component: it contains static values, external image URLs, inline SVG/chart artwork and no verified FastAPI data flow.

## Export inventory

### Export 1 (12 screens)

`candidate_hypotheses_formulation_evaluation_workspace`, `detected_sources_scientific_source_catalog`, `evidence_review_atomic_evaluation_workspace`, `file_validation_compatibility_gate_diagnostic`, `fits_image_explorer_astronomical_workspace`, `new_investigation_file_ingestion_staging_workspace`, `observations_scientific_product_catalog`, `pipeline_analysis_processing_console`, `scientific_reports_immutable_dossier_publication_workspace`, `spatial_analysis_astrometric_matching_morphology_workspace`, `spectral_analysis_sed_continuum_emission_modeling_workspace`, `temporal_analysis_multi_epoch_time_series_workspace`.

`obsidian_deep_sky_telemetry` is also present as an auxiliary visual/design asset directory but does not provide a normal screen pair in the inventory.

### Export 2 (13 screens)

`cosmos_astronomical_scientific_investigation_platform`, `cosmos_demo_mode_with_interactive_celestial_physics`, `cosmos_overview_mission_control`, `explore_demo_astronomical_observation_catalog`, `file_validation_compatibility_gate_diagnostic`, `hypotheses_formulation_candidate_matrix`, `hypothesis_comparison_multi_model_bayesian_likelihood`, `image_explorer_astronomical_fits_viewer_workspace`, `new_investigation_ingestion_staging_workspace`, `pipeline_analysis_processing_console`, `planetary_computer_earth_observation_stac_workspace`, `report_history_immutable_dossiers_audit_log`, `spatial_analysis_astrometric_matching_morphology`.

`obsidian_deep_sky_telemetry` is again auxiliary rather than a standard page pair.

## Visual system findings

Both exports converge on a dark observatory/control-room language: near-black backgrounds, cyan or violet active states, thin borders, monospace metadata, dense left navigation and fixed telemetry/status bars. Export 1 is generally more coherent as a scientific workstation: it has a consistent shell, catalog/detail split panes and explicit provenance blocks. Export 2 is more ambitious in overview and image exploration, but several screens contain highly specific sample claims that cannot be used as COSMOS data.

The strongest recurring patterns are:

- Persistent left navigation grouped by mission, data workspace, scientific analysis, investigation and reporting.
- A top operational status/header strip.
- Large workspace title with a short scientific context line.
- Two-column inspector layouts: data/list on the left, selected product/evidence detail on the right.
- IBM Plex Mono/JetBrains Mono-style metadata, coordinate readouts and status labels.
- Thin cyan focus rules and restrained cyan/violet status colors.
- Dark image/chart canvases with explicit axes, units and legends.
- Bottom status bars for WCS, frame, calibration and system state.

## Scientific integrity concerns in the mockups

Several screens contain fictional or unsupported values, identities and claims (for example named Barnard’s Star measurements, calibrated response conclusions, SED model parameters, proper motion, Bayesian percentages and telescope telemetry). These must be replaced by backend values, `UNTESTABLE` states or empty states in a real implementation. The HTML designs must not be copied as data.

## Main design weaknesses

- Some screens use nested card stacks and heavy borders, creating a dashboard-like density.
- A few screens use pulsing dots or “live” telemetry without a verified live data source.
- Export 2 sometimes uses decorative starfields as if they were observation context; decorative imagery must remain separate from FITS previews.
- Typography is often too small and overly monospace for explanatory content.
- Several charts are static SVG illustrations rather than interactive backend-driven visualizations.
- Navigation labels and workspace naming vary between exports.

## Duplicate/variant comparison

The exports do not contain identical screen folders; overlap is by workspace concept. Export 1 has stronger coverage of Evidence Review, Detected Sources, Observations, Spectral Analysis and Temporal Analysis. Export 2 adds Overview/Mission Control, Explore Demo, Planetary Computer, Report History, Hypothesis Comparison and a richer FITS viewer. Where both provide a concept, Export 1 is usually the more complete workstation variant; Export 2 is stronger for entry/overview and image-viewer composition.
