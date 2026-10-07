# VisionPark

VisionPark uses FastAPI, React, PostgreSQL and a real YOLO + PaddleOCR pipeline.
Application mock providers, fixture fallbacks and the development mock API have been removed.

## Current implemented workflows

- Login, JWT/RBAC, administration of users and lanes, account profile/password and session revocation.
- Station accepts JPEG/PNG images or a local MP4. Video frames use the same recognition API as images.
- Preview does not persist. Saving a final capture writes image and detection metadata to persistent storage.
- Confirmation/correction and manual entry create a database parking transaction with audit and idempotency protection.
- Detection, parking and audit histories use server filtering, totals and pagination.
- Theme/language preferences, notifications/read state and sanitized error events use database APIs.

Vehicle checkout, payment, pricing, monthly passes, barrier control and live RTSP are outside the current implementation. Fire detection training is deferred.
Real-vehicle accuracy and video latency acceptance still require a licensed, labelled dataset; model readiness alone does not prove these metrics.

## Docker setup

Copy `env.example` to `.env`, supply unique credentials and `JWT_SECRET_KEY`, and provision model assets:

```powershell
py -3 backend/scripts/provision_real_docker.py
docker compose up --build -d
docker compose ps
```

The example selects `docker-compose.yml` plus `deployment/compose.real.yml`. Model weights, OCR assets and the Docker manifest are mounted read-only. Missing or invalid models report ALPR unavailable; there is no fake recognition fallback.
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
