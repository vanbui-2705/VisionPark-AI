# ALPR model assets

This directory stores versioned model metadata only. Model weights are runtime
assets and are intentionally excluded from Git.

The manifest is the handoff contract for assets distributed outside Git: copy
the declared weight to `backend/app/alpr/weights/`, verify its SHA-256 checksum,
and keep `ALPR_PROVIDER=mock` when the asset is unavailable. CI and clean
checkout tests never download model weights.

- Manifest: `alpr-manifest.json`
- Local weight location: `../app/alpr/weights/best.pt`
- Real runtime dependencies: `pip install -e ".[dev,real]"`
- Runtime default: keep `ALPR_PROVIDER=mock` until the `.pt` provider is
  verified against the ALPR runtime contract.

For a local real-provider run from `backend`:

```powershell
$env:ALPR_PROVIDER = "real"
python -m uvicorn app.main:app --reload
```

Set `VITE_USE_MOCK_ALPR=false` in the frontend environment so captured frames
are sent to the backend instead of the frontend fixture.
