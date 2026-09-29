# Phase 1 smoke checklist

Phase 1 acceptance does not require OCR. The default provider is deterministic
mock; the trained `.pt` path is detector-only when `ALPR_OCR_ENABLED=false`.

## Local checks

- [ ] Copy `.env.example`, set demo passwords and keep `ALPR_PROVIDER=mock`.
- [ ] Run `alembic upgrade head` and `alembic check` on a disposable database.
- [ ] Start backend and frontend; verify `/health/live` returns `200`.
- [ ] Verify `/health/ready` reports database and ALPR readiness.
- [ ] Login as `admin` and `operator`; verify Lane list and Admin-only mutation.
- [ ] Upload a JPEG/PNG frame with an active Lane; verify detection is persisted.
- [ ] Verify invalid MIME, corrupt image and oversized image return `422`.
- [ ] Verify mock scenarios `low-confidence`, `no-plate`, `unavailable` and
  `processing-error` map to confirmation/`503` behavior.
- [ ] Confirm or correct a detection; verify history and audit entry.
- [ ] Verify Station captures at most one request and draws the bbox.
- [ ] Verify the UI says OCR is deferred when the plate is null.

## Container gate

- [ ] Run `docker compose up --build -d` on a clean machine.
- [ ] Verify `db`, `migrate`, `backend` and `frontend` are healthy.
- [ ] Repeat login → Lane → frame → result → confirmation after a clean restart.
