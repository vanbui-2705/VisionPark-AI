# Phase 2 runbook

## Mock CI/local gate

From `backend`:

```powershell
py -3 scripts/release_gate.py
```

This validates all deterministic mock scenarios, confirms real-provider
not-ready behavior when the manifest is missing, runs the benchmark, pytest and
Ruff. It does not download weights or require a GPU. Reports are written under
`backend/var/benchmarks/`, which is ignored by Git.

The frontend gate is run from `frontend`:

```powershell
npm run test -- --run
npm run lint
npm run build
```

## Real provider demo

Provision the `.pt` asset outside Git at the path declared by
`backend/models/alpr-manifest.json`, verify its SHA-256, install
`.[dev,real,ocr]`, and set:

```powershell
$env:ALPR_PROVIDER = "real"
$env:ALPR_OCR_ENABLED = "true"
$env:VITE_USE_MOCK_ALPR = "false"
py -3 scripts/benchmark_alpr.py --provider real --split smoke
```

Readiness must be `ready` only after both detector and OCR load. If the model,
manifest, dependency or OCR cache is unavailable, rollback is:

```powershell
$env:ALPR_PROVIDER = "mock"
$env:ALPR_OCR_ENABLED = "false"
$env:VITE_USE_MOCK_ALPR = "true"
```

## Failure and duplicate checks

Run the existing integration suite for restart/migration, provider timeout,
duplicate `PARKED` rejection, idempotency retry, audit and authorization:

```powershell
cd backend
py -3 -m pytest tests/integration -q
```

The Station flow sends preview frames with `persist=false`. Only the separate
check-in request creates a `PARKED` transaction and uses an idempotency key.
Capture screenshots or screen recordings for success, low confidence, no plate,
manual correction, duplicate and retry in the local evidence folder; never
commit private vehicle footage or model weights.
