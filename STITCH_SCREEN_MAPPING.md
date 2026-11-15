# Stitch screen mapping

Recommended source variant for each COSMOS workspace:

| COSMOS workspace | Recommended Stitch screen | Source | Rationale and adaptation |
|---|---|---|---|
| Overview / Mission Control | `cosmos_overview_mission_control` | Export 2 | Strongest entry shell and investigation context; replace fictional queue/telemetry with real state. |
| Explore Demo | `explore_demo_astronomical_observation_catalog` | Export 2 | Best catalog/discovery composition; preserve explicit demo labeling. |
| New Investigation | `new_investigation_ingestion_staging_workspace` | Export 2 | Cleaner staging flow; connect to actual multipart upload. |
| File Upload | `new_investigation_file_ingestion_staging_workspace` | Export 1 | More explicit file staging/product rows. |
| File Validation | `file_validation_compatibility_gate_diagnostic` | Export 1 | Strongest diagnostic hierarchy; use actual parser/gate results. |
| Processing Progress | `pipeline_analysis_processing_console` | Export 1 | More complete pipeline event presentation; do not imply progress not returned by backend. |
| Investigation Summary | `cosmos_astronomical_scientific_investigation_platform` | Export 2 | Best high-level scientific workstation composition. |
| FITS Image Explorer | `image_explorer_astronomical_fits_viewer_workspace` | Export 2 | Strongest image canvas and inspector; replace sample image with authentic preview endpoint. |
| Observations | `observations_scientific_product_catalog` | Export 1 | Best product catalog/detail inspector. |
| Detected Sources | `detected_sources_scientific_source_catalog` | Export 1 | Unique screen and appropriate source catalog structure. |
| Temporal Analysis | `temporal_analysis_multi_epoch_time_series_workspace` | Export 1 | Unique, readable time-series composition; preserve missing epochs and uncertainty. |
| Spectral Analysis | `spectral_analysis_sed_continuum_emission_modeling_workspace` | Export 1 | Strong chart/inspector layout; remove unsupported SED fits and emission interpretations. |
| Spatial Analysis | `spatial_analysis_astrometric_matching_morphology_workspace` | Export 1 | More explicit astrometric/morphology inspector; use only valid WCS measurements. |
| Evidence Review | `evidence_review_atomic_evaluation_workspace` | Export 1 | Unique evidence-oriented layout; map every value to evidence API. |
| Hypotheses | `hypotheses_formulation_candidate_matrix` | Export 2 | Strong candidate matrix; preserve user/pipeline distinction. |
| Hypothesis Comparison | `hypothesis_comparison_multi_model_bayesian_likelihood` | Export 2 | Unique comparison surface; remove invented probabilities and winners. |
| Scientific Reports | `scientific_reports_immutable_dossier_publication_workspace` | Export 1 | Strong publication/dossier layout; render stored snapshot only. |
| Report History | `report_history_immutable_dossiers_audit_log` | Export 2 | Explicit history/audit presentation; connect persisted report metadata. |
| Planetary Computer | `planetary_computer_earth_observation_stac_workspace` | Export 2 | Correctly scoped external-data workspace; retain separation from SPHEREx. |
| Demo mode | `cosmos_demo_mode_with_interactive_celestial_physics` | Export 2 | Use only as explicitly labelled synthetic/demo entry; no fabricated physics claims. |

## Reusable components

- Global shell: sidebar, top status/header, investigation selector, progress tracker, bottom provenance/status bar.
- `WorkspaceHeader`: title, context, status and actions.
- `StatusPill`: READY, PARTIAL, UNTESTABLE, INCONCLUSIVE, FAILED.
- `MetadataGrid`: IDs, timestamps, detector, units, hashes and provenance.
- `ScientificPanel`: translucent surface with readable hierarchy.
- `DataTable`/catalog rows with selected state and inspector panel.
- `ChartCanvas`: zoom/pan/reset, axes, units, uncertainty and empty states.
- `ProvenanceDrawer`: product, observation, hash, source and limitations.
- `CompatibilityGate`: gate decision plus explicit reasons.

## Screen-specific components

FITS viewer requires image/HDU/layer selectors, authentic preview, WCS/pixel inspection, display-stretch disclosure and source overlays. Temporal requires source/epoch selection and error bars. Spectral requires wavelength/response/calibration status. Spatial requires WCS-aware coordinates, association and morphology. Evidence/hypothesis screens require evidence roles and persistent lifecycle controls. Reports require immutable snapshot navigation and format downloads.
