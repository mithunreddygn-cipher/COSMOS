# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing Python scientific engine and React application (Vite, TypeScript). The Python engine is authoritative for scientific calculations; the frontend must not duplicate them.

## Users

Astronomy enthusiasts, university students, researchers, and scientific investigators who want to explore astronomical observations, identify unusual phenomena, and investigate possible explanations. COSMOS should be approachable to beginners while retaining scientific depth for experienced users.

## Product Purpose

COSMOS is an evidence-driven astronomical investigation platform. It supports exploration and ingestion of astronomical observations, particularly SPHEREx data; inspection of sources and observational properties; detection of unusual patterns and potential anomalies; comparison across time, wavelength, and spatial characteristics; evaluation of competing hypotheses; and generation of traceable scientific investigation reports.

Its investigation workflow is EXPLORE → COMPARE → DISCOVER → INVESTIGATE → UNDERSTAND.

## Positioning

COSMOS emphasizes scientific investigation rather than simply displaying detections. Its guiding principle is: “Every anomaly is a question. Every observation is evidence. Every explanation is a hypothesis.” Results must be traceable to their underlying observations, measurements, processing steps, uncertainties, and limitations. The Evidence Orbit represents how an observation moves through validation, compatibility checks, temporal, spectral, and spatial analysis, hypothesis evaluation, and a supported conclusion or explicitly documented limitation.

## Operating Context

Users explore and ingest astronomical observations, inspect sources, compare observations across time, wavelength, and space, identify unusual patterns, investigate competing explanations, and produce reproducible reports. The scientific workspace takes priority over a marketing website or decorative dashboard.

## Capabilities and Constraints

- Preserve the existing Python scientific engine as the authoritative source of scientific calculations; do not duplicate those calculations in the React frontend.
- Maintain existing backend API contracts and scientific functionality.
- Preserve uncertainty, provenance, compatibility states, and scientific limitations.
- `UNTESTABLE` must never be interpreted as a negative result or as absence of a signal.
- Never fabricate astronomical observations, measurements, discoveries, or scientific conclusions.
- Clearly distinguish authentic observational data, scientific renderings, synthetic simulations, and decorative artwork. Label synthetic demonstrations as synthetic.
- Build on the existing React application; do not create disposable prototypes or duplicate applications.
- Prioritize a functional scientific workspace over a marketing website or decorative dashboard.
- Make the interface intuitive for beginners while keeping advanced scientific information accessible.
- Support performance, responsive layouts, accessibility, and reduced motion.

## Brand Commitments

The product is named COSMOS. The user describes its direction as a premium scientific exploration environment with the sophistication of a space-technology product: a near-black, deep-space foundation, subtle atmospheric lighting, layered depth, restrained glass surfaces, refined editorial and technical typography, and purposeful motion that communicates scientific processes. Avoid generic AI-generated dashboard aesthetics, excessive blue and purple gradients, oversized decorative spheres, repetitive cards, random glowing elements, and generic particle backgrounds. Visual sophistication must not compromise usability, performance, scientific integrity, or functional completeness.

## Evidence on Hand

The repository contains an existing Python scientific engine, Streamlit Mission Control, a React frontend, scientific documentation, and a bundled synthetic demonstration. The README states that synthetic demonstrations are labeled synthetic and are not real SPHEREx observations or discoveries. Detection algorithms are screening methods, not a validated discovery pipeline; no candidate is a discovery claim. See `README.md`, `BUILD_STATUS.md`, `docs/real_data_audit.md`, and `docs/react_backend_integration.md` for implementation status, evidence, and limitations.

## Product Principles

- Treat every anomaly as a question, every observation as evidence, and every explanation as a hypothesis.
- Keep every result traceable to its data, processing, uncertainty, and limitations.
- Preserve scientific uncertainty; unavailable or untestable evidence is not a negative result.
- Let scientific function and integrity guide the workspace.
- Support beginners without hiding advanced scientific detail.
