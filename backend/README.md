# VisionPark backend

FastAPI modular monolith with PostgreSQL/Alembic, Argon2id/JWT, role guards and real YOLO/PaddleOCR.

## Local development

Use Python 3.12 and a dedicated database. Copy `.env.example` to `.env`, set `DATABASE_URL` and a unique `JWT_SECRET_KEY` of at least 32 characters.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,real,ocr]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`ALPR_PROVIDER=real` is the only supported provider. The approved detector and OCR inference assets are bundled in the repository and Docker image. `scripts/provision_real_docker.py` remains available for the optional mounted-model override. Readiness reports missing assets or inference dependencies instead of returning a fixed plate.
`AUTO_SEED=false` by default. Explicit bootstrap requires an administrator password and never resets an existing account. There are no automatically created example lanes/operators.

## API workflows

- `/api/v1/auth/login`, `/me`, `/change-password`, `/logout`, `/preferences`.
- `/api/v1/users/{id}/revoke-sessions` for administrators; JWT versions reject revoked sessions.
- `/api/v1/alpr/detections`: JPEG/PNG multipart, `mode=preview|final`, `capture_id`, `input_kind=IMAGE_UPLOAD|VIDEO_FRAME`, optional `video_time_ms`.
- `/api/v1/alpr/detections/{id}/confirm` and canonical parking check-in provide transactional audit/idempotency.
- Detection/parking/audit lists support server filters and optional `paginated=true` envelopes.
- `/api/v1/notifications`, read/read-all; receiver isolation applies.
- `/api/v1/errors`: authenticated sanitized reporting; administrator listing; bounded reports, correlation IDs and selected backend failures.

Preview writes no detection/image. Final writes one image and its metadata. Test doubles are restricted to tests and excluded from the runtime Docker image.

## Verification and operations

```powershell
python -m pytest tests
python -m ruff check app scripts tests
python -m ruff format --check app scripts tests
python scripts/audit_media.py
```

The media audit reports missing/orphan files without deletion. Full backup and isolated restore instructions are in [the runbook](../docs/real-data-runbook.md).

GitHub CI uses `deployment/compose.ci.yml` with isolated CI volumes and bundled
YOLO/OCR assets. It verifies asset checksums, installs CPU inference dependencies,
waits for actual model warmup and requires `/health/ready` HTTP 200 with OCR enabled.
Frontend health is also checked; runtime logs are collected on failure.
Training checkpoints and download caches remain outside Git. This startup check
does not replace the labelled real-vehicle accuracy benchmark.
