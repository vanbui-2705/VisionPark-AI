# M5 no-PCCC enhancement patch (2026-10-18)

This patch EXTENDS the earlier M5-no-fire-development.zip. It is not a certified complete M5 implementation.

## Installation on Windows

1. Keep your existing database backup. Stop backend and frontend.
2. Copy folders `backend/` and `frontend/` from this ZIP into `D:\HocTap\VisionPark-AI-Latest\`, merging and replacing files. Do not delete other files.
3. `cd /d D:\HocTap\VisionPark-AI-Latest\backend`
4. `.venv\Scripts\activate`
5. `python -m pip install -e .` (adds reportlab for PDF)
6. `python -m compileall -q app\modules\m5`
7. `python -m alembic current` (expect 20261018_0015; do not upgrade again if already at head)
8. `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
9. In another terminal: `cd /d D:\HocTap\VisionPark-AI-Latest\frontend` then `npm run build` and `npm run dev`.
10. Sign in, navigate to `http://localhost:5173/admin/m5`. Use an account with dashboard.read permission.

## Added features
- GET `/api/v1/m5/daily-stats.pdf` uses the same filters, permissions and rows as CSV.
- GET `/api/v1/m5/devices/alerts` lists OFFLINE / DEGRADED devices at request time.
- Frontend `/admin/m5` page: building selector, dates, dashboard, daily stats, CSV/PDF downloads, devices and polling alerts.
- Daily rebuild script now configures database connection before using it. Run manually: `python -m app.modules.m5.rebuild_daily --day 2026-10-17`. For automation configure Windows Task Scheduler separately.

## Known incomplete areas (DO NOT mark entire M5 complete)
- Occupancy peak still placeholder 0. Capacity/availability still unknown.
- Device alerts are polled, not pushed to users; no persisted alert records or notification delivery.
- No complete integration/E2E suite or tested multi-building tenant isolation in this environment.
- Daily stats require manual rebuild or external scheduled task.
- No fire/PCCC code is included.

## Validation
Python source syntax checked. The user's PostgreSQL, Windows virtualenv, and frontend build are not accessible here, so real DB tests and `npm run build` on Windows are still required.
