# VisionPark

VisionPark uses FastAPI, React, PostgreSQL and a real YOLO + PaddleOCR pipeline.
Application mock providers, fixture fallbacks and the development mock API have been removed.

## Current implemented workflows

- Login, JWT/RBAC, administration of users and lanes, account profile/password and session revocation.
- Station accepts JPEG/PNG images or a local MP4. Video frames use the same recognition API as images.
- Preview does not persist. Saving a final capture writes image and detection metadata to persistent storage.
- Confirmation/correction and manual entry create a database parking transaction with audit and idempotency protection.
- Parking checkout supports fee preview, CASH collection, monthly entitlement, lost-ticket handling, counter updates and audit events.
- Detection, parking and audit histories use server filtering, totals and pagination.
- Theme/language preferences, notifications/read state and sanitized error events use database APIs.

VisionPark is an operational system in `FILE_UPLOAD` mode: Station accepts JPEG/PNG files and
local MP4 video, then submits image bytes or extracted video frames to the real ALPR provider.
Live camera/RTSP ingestion is not integrated yet. Physical barrier-controller status must be
reported separately from the persisted barrier business events. Fire detection training is deferred.
The tracked licensed dataset and benchmark establish the current recognition-quality baseline;
model readiness alone does not prove accuracy.

## Phase 2 status

System workflow and recognition quality are evaluated independently. The system gate exercises
the real stack in `FILE_UPLOAD` mode; the quality gate only evaluates the real provider against
independently labelled media. Exit codes are `0=PASS`, `1=FAIL`, and `2=HOLD`.

```powershell
cd backend
$env:SEED_OPERATOR_PASSWORD = '<local operator password>'
py -3 scripts/system_gate.py --image <path-to-image> --video <path-to-mp4>
py -3 scripts/release_gate.py --dataset datasets/phase2-release.json
```

`system_gate.py` reports `HOLD` when the deployed backend/frontend or required acceptance media
are unavailable. `release_gate.py` reports `HOLD` when the real media/model evidence is missing;
it never generates inference input from `expected_plate` or a synthetic OCR label.

See the [Phase 2 release report](docs/phase-2-release-report-2026-10-09.md) and
[evidence index](docs/phase-2-evidence/evidence-index.json).

## Docker setup

Copy `env.example` to `.env`, supply unique credentials and `JWT_SECRET_KEY`, and provision model assets:

```powershell
py -3 backend/scripts/provision_real_docker.py
docker compose up --build -d
docker compose ps
```

The example selects `docker-compose.yml` plus `deployment/compose.real.yml` for existing mounted-model installations. Plain `docker compose -f docker-compose.yml up --build -d` uses the detector and OCR assets bundled in the image. GitHub CI also uses bundled assets and requires real YOLO/OCR readiness HTTP 200. Missing or invalid models report ALPR unavailable; there is no fake recognition fallback.
Default ports are frontend 5173, backend 8000 and PostgreSQL 5433; this workspace can override them in `.env`.

`AUTO_SEED=false` is the default. For a new installation, provide `SEED_ADMIN_PASSWORD` and temporarily enable `AUTO_SEED=true` to create an initial administrator. It preserves existing accounts and passwords and creates no demonstration lanes or operator account. Create lanes and operators through administration.
Public registration is disabled by default and, when enabled, only creates operators.

## Persistent data

Operational volumes are explicitly named `visionpark_postgres_data` and `visionpark_media_data`.
Restart, rebuild and recreation keep these volumes. Database migrations add fields and tables without deleting existing records.
Never run `docker compose down -v`, volume pruning, or delete the media directory when preserving data.
Backup database and media together before upgrades; restore into a separate environment first.

See [data preservation runbook](docs/real-data-runbook.md), [backend setup](backend/README.md), and [implementation checklist](openspec/changes/complete-real-data-system/tasks.md).

## Verification

```powershell
cd backend
py -3 -m pytest tests
py -3 -m ruff check app scripts tests
cd ../frontend
npm test -- --run
npm run lint
npm run build
```

Tests use isolated databases and test doubles under `backend/tests`; these are not recognition providers available to the deployed application.
PostgreSQL race tests require `TEST_POSTGRES_URL` pointing to a disposable server where temporary databases may be created.

## Functional acceptance and E2E

See [operational runbook](docs/System-Functional-Runbook.md) for GATE_* credentials, nonzero CASH acceptance pricing, preflight, dry-run and troubleshooting. `system_gate.py` writes real acceptance sessions; use a dedicated quiet acceptance building. Its JSON explicitly does not evaluate ALPR accuracy. `scripts/dry_run.py` runs functional and quality gates independently.
