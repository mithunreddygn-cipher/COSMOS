# COSMOS Release Status

## Scope

This release pass applied one focused engineering correction: per-investigation
in-process locking around manifest read-modify-write operations. Scientific
algorithms, API contracts, storage formats and frontend design were not changed.

## Architecture

COSMOS retains its modular Python scientific engine, FastAPI adapter, local
investigation-scoped product storage, persistent hypotheses, immutable report
snapshots, React/Vite frontend, and Streamlit fallback. Real and synthetic FITS
data remain explicitly separated.

## Persistence and concurrency

`api/product_storage.py` now maintains independent re-entrant locks keyed by
investigation ID. Product persistence, investigation creation, product updates
and investigation updates hold the relevant lock only around manifest mutation.
Temporary files and replacement semantics are preserved. Locks release through
`finally`, including exceptions. Different investigations do not block one
another within a process.

This is process-local protection. A multi-process deployment still requires a
filesystem lock or database-backed coordination before it can be considered
safe for concurrent writers.

## Scientific and security controls

- Chunked upload hashing and size enforcement remain enabled.
- Generated product filenames and strict identifier validation prevent path traversal.
- Product paths are resolved inside investigation directories.
- FITS data, variance, flags, WCS and provenance remain authoritative inputs.
- Compatibility Gate statuses and `UNTESTABLE` semantics are unchanged.
- Planetary Computer access remains host- and redirect-validated.

## Verification

Added regression coverage for concurrent same-investigation uploads, independent
investigation uploads, hash preservation and lock release after a write failure.

The requested asynchronous storage tests could not complete in this managed
Windows environment: creating an asyncio event loop blocks in the OS socketpair
initialisation path. This is the previously observed environment-specific
Streamlit/asyncio limitation, not an assertion failure in the storage code.

Completed checks:

- Python source compilation: executed after the change.
- Frontend TypeScript check: PASS.
- Frontend production build: PASS.

The product, investigation, hypothesis, report and API regression groups must be
rerun on a normal Windows installation where asyncio loop creation works.

## Known release blockers

1. Validate the asynchronous regression tests outside the restricted environment.
2. Run the complete Python suite; the managed environment previously stalls in
   the Streamlit AppTest path.
3. Execute browser acceptance and live restart tests on a machine permitting
   localhost sockets.
4. Validate dependencies with network access (`npm audit`/equivalent).
5. Obtain multiple compatible real SPHEREx epochs before claiming scientific
   production readiness.

## Commands

Backend:

```powershell
.venv\Scripts\python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

Focused tests:

```powershell
.venv\Scripts\python -m pytest tests/test_product_storage.py tests/test_investigation_storage.py tests/test_hypothesis_storage.py tests/test_report_storage.py tests/test_api.py -q
```

Compilation and frontend checks:

```powershell
.venv\Scripts\python -m compileall api ingest science detect investigate gate
cd frontend
npx tsc --noEmit
npm run build
```

## Readiness classification

- Software functionality: **PARTIAL**
- Engineering readiness: **PARTIAL**
- Scientific validation: **NOT READY** for multi-epoch conclusions
- Production readiness: **NOT READY**

