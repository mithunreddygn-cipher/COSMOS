# Stitch implementation plan

This plan is for approval only. No Stitch export has been copied into production React and no application files were modified during the audit.

## Phase 1 — establish the shell

Reuse the existing React state/API shell and introduce component boundaries without changing endpoint contracts:

`AppShell`, `SidebarNavigation`, `WorkspaceHeader`, `InvestigationContext`, `ProgressTracker`, `StatusPill`, `ProvenancePanel`.

Use the strongest common visual language from Export 1 and Export 2: near-black glass surfaces, visible starfield only as atmosphere, readable sans-serif interface text, IBM Plex Mono for scientific values, thin active rules and stable layouts. Do not use generated HTML’s fictional telemetry.

## Phase 2 — observation and ingestion flow

Implement `ExploreWorkspace`, `NewInvestigationWorkspace`, `ValidationWorkspace` and `ProcessingWorkspace` around the existing upload/product/manifest APIs. States must include loading, invalid product, partial success, unsupported format, corrupted FITS and `UNTESTABLE` gate reasons.

## Phase 3 — scientific analysis workspaces

Build adapters around the existing Image Explorer, Temporal, Spectral and Spatial components. React should format and visualize backend results only. Preserve original FITS previews, uncertainty, flags, WCS validity, calibration evidence and provenance. Do not use static SVG values from Stitch.

## Phase 4 — investigation and reporting

Refine Evidence Review, Hypotheses, Comparison, Scientific Reports and Report History using the selected mappings. Keep user-authored hypotheses separate from pipeline cards; never render unsupported confidence/probability values.

## Phase 5 — external data and demo

Keep Planetary Computer under its dedicated external-data API namespace. Keep demo mode visibly synthetic and never mix it with real observation evidence.

## Background and interaction guidance

The existing COSMOS visual assets can provide atmosphere, but scientific canvases must remain readable and authentic. Background parallax, if implemented, should affect only decorative layers; it must not move charts, image pixels, source overlays or metadata panels. Respect reduced motion and provide static fallback. Avoid pulsing “live” indicators unless backed by a real changing status.

## Validation gates before implementation is accepted

1. TypeScript and production build pass.
2. API integration tests pass for every mapped endpoint.
3. Synthetic FITS workflow remains explicitly labelled and passes regression tests.
4. Real FITS previews retain provenance and original data semantics.
5. Empty, loading, failed, partial and `UNTESTABLE` states are rendered for every workspace.
6. Browser screenshots are captured on Windows 11 with FastAPI and Vite running.
7. No Stitch static sample claims remain in production UI.

## Designs that cannot be copied exactly

- Static external image URLs must be replaced by local/public approved assets or authentic FITS API previews.
- Fictional telescope telemetry, named source identities, calibrated measurements, Bayesian probabilities and scientific conclusions cannot be used without backend evidence.
- Static SVG charts must become data-driven visualizations or clearly labelled illustrative placeholders.
- Stitch’s HTML/Tailwind structure cannot replace the current API/state architecture; it must be translated into maintainable React components.
