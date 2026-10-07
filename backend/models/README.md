# Bundled demo model assets

The demo repository and runtime Docker image include the approved YOLO detector
`backend/app/alpr/weights/best.pt` and the pretrained PaddleOCR recognition model
`ocr/latin_PP-OCRv5_mobile_rec/`. OCR's upstream model card is retained beside its
inference files. Training datasets, checkpoints and download caches are excluded.

`alpr-manifest.json` records model version, detector checksum, OCR paths and checksums.
Run `python backend/scripts/verify_model_bundle.py` from the repository root.

The real CPU runtime needs `backend[real,ocr]`; Docker CI installs CPU PyTorch,
Ultralytics and PaddleOCR and verifies readiness HTTP 200 after actual warmup.
OCR uses the bundled directory, so startup does not download recognition weights.
There is no mock provider fallback. Missing/corrupt models must fail readiness.

The optional `deployment/compose.real.yml` still supports separately provisioned
local assets. Ordinary images and CI use the bundled manifest directly.
