# COSMOS local API

Install the optional API runtime and launch locally:

```powershell
python -m pip install -e ".[api]"
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

The adapter calls `inspect_paths` and `run_fits_pipeline` directly. It does not reproduce scientific calculations in JavaScript, accept client-supplied scientific verdicts, or expose uploaded files beyond the request lifecycle.
