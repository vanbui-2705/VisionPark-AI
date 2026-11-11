# System functional acceptance — BUILD-06/07, IMPROVE-06/07

## Scope and results

This is the real application in `FILE_UPLOAD` mode (JPEG/PNG and frames decoded
from local MP4). `LIVE_CAMERA/RTSP` is NOT_INTEGRATED. The current checkout adapter
returns `barrier_mode=SIMULATED`: the persisted event is not a physical controller
ACK. Do not infer physical movement from `barrier_opened=true`.

`system_gate.py` exercises the deployed API, real PostgreSQL, frontend health,
real image/video inference transport, check-in, duplicate protection, checkout
CASH, replay, invoice/payment IDs and amounts, counter deltas, dashboard, cash-shift
report and audit. It also exercises manual check-in/CASH without calling inference.
It does **not** compare OCR with labels and always reports
`alpr_accuracy=NOT_EVALUATED`. `release_gate.py` independently measures ALPR quality
on labelled media; its PASS/FAIL/HOLD must be reported separately.

Both gates: 0 PASS, 1 FAIL, 2 HOLD. Every unmet condition is nonzero. Missing runtime,
credentials/media or commit provenance is HOLD; malformed data, wrong HTTP status,
or business inconsistency is FAIL. An HTTP timeout during a write is inconclusive:
inspect the recorded session/idempotency keys before retrying.

## Preflight

- Use a dedicated, quiet acceptance building and operator; no concurrent human
  activity during report/counter delta checks. The gate writes real test sessions,
  detections, invoices and payments and leaves them as evidence. Never aim it at
  production. There is no automatic delete/reset of operational data.
- Back up database **and** media before upgrades. Record commit SHA, environment,
  model manifest, frontend/backend URLs and acceptance media provenance/rights.
- Configure the operator's building membership, finish temporary-password change,
  activate one IN and one OUT lane in the same building, set capacity and effective
  CAR/HOURLY pricing with a customer class. For the automated immediate CASH case,
  use `free_minutes=0`, `initial_fee>0`; a zero-fee transaction cannot prove payment.
- Provide a real JPEG/PNG and MP4. The gate validates decoding and records SHA-256.
  Select a plate from the image for operator confirmation; it is not OCR ground-truth
  scoring. Use no production customer data in exported evidence.
- Default ports: frontend 5173, API 8000, PostgreSQL host 5433/container 5432.
  Check `.env` overrides and free these ports before starting.
- From repository root: `docker compose config --quiet`, then
  `docker compose up --build -d`, then `docker compose ps`.
- Wait for model warmup: `docker compose logs --tail 100 backend` and
  `curl --fail http://127.0.0.1:8000/health/ready`. Require database provider
  `postgresql`, both statuses `ready`, ALPR provider `real` and `ocr_enabled=true`.
  CPU cold start can take several minutes; liveness alone is not readiness.
- Verify `curl --fail http://127.0.0.1:5173/health/live` and open the frontend.
  The gate targets the Docker/Nginx frontend, not Vite's fallback HTML health route.

## Credentials and acceptance environment

Keep credentials in the process environment, an ignored `.env`, or CI secrets.
Never paste tokens/passwords into reports or commit real values. The gate reads
`GATE_*`; it does not create users or assume a seeded operator exists.

PowerShell (set IDs to those from your acceptance administration screens):

```powershell
$env:GATE_ENVIRONMENT = 'acceptance-local'
$env:GATE_COMMIT = (git rev-parse HEAD)
$env:GATE_USERNAME = Read-Host 'Acceptance operator username'
$secret = Read-Host 'Acceptance operator password' -AsSecureString
$env:GATE_PASSWORD = [System.Net.NetworkCredential]::new('', $secret).Password
$env:GATE_IN_LANE_ID = Read-Host 'IN lane UUID'
$env:GATE_OUT_LANE_ID = Read-Host 'OUT lane UUID'
$env:GATE_CUSTOMER_CLASS_ID = Read-Host 'Customer class UUID'
$env:GATE_PLATE = Read-Host 'Acceptance image plate'
```

For a ZIP checkout without `.git`, set `GATE_COMMIT` to the source SHA from the
handover; do not invent a commit. The environment name and SHA are recorded, while
passwords, tokens and database connection URLs are excluded.

## Dry-run commands

Use Python 3.12 with backend dev dependencies installed (`pip install -e '.[dev]'`
from `backend`). For the local ALPR quality gate also install `[real,ocr]` and
provision the model assets. Use absolute paths for external acceptance media.

```powershell
cd backend
python scripts/system_gate.py --image C:/acceptance/car.jpg --video C:/acceptance/drive.mp4
# Inspect $LASTEXITCODE immediately. JSON: backend/var/reports/system-functional-gate.json
python scripts/dry_run.py --image C:/acceptance/car.jpg --video C:/acceptance/drive.mp4 --dataset datasets/phase2-release.json
# Runs both gates even when the first fails; separate reports under var/reports.
Remove-Item Env:GATE_PASSWORD
```

On bash use the equivalent exported environment variables and paths, then inspect
`$?`. Override `--backend-url` and `--frontend-url` for mapped ports. Functional
PASS does not make ALPR quality PASS. `dry-run.json` contains the two exit codes;
its combined exit is nonzero if either gate is not PASS.

## Same checks as CI

CI uses Python 3.12, Node 24 and PostgreSQL 17 in Docker. The database for tests is
an isolated `test-db` service with temporary storage; tests create/drop uniquely
named databases there, never on the application's database. PostgreSQL race tests
run both same-key and different-key concurrent checkout requests. They may be
skipped locally without PostgreSQL, but CI sets `TEST_POSTGRES_URL` so they run.

From repository root, with ephemeral `JWT_SECRET_KEY` and `CI_TEST_DB_PASSWORD`
exported (generated by CI; choose fresh random values locally):

```bash
export COMPOSE_PROJECT_NAME=visionpark-ci
export COMPOSE_FILE=docker-compose.yml:deployment/compose.ci.yml
docker compose --profile ci build backend-ci frontend-ci migrate
docker compose --profile ci run --rm backend-ci
docker compose --profile ci run --rm frontend-ci
```

Backend container runs pytest, ruff lint and ruff format check. Frontend runs lint,
Vitest and production build. Station/settings lint warnings fail CI specifically;
existing unrelated UI warnings are reported without hiding them. Bundle tuning is
deferred until operational acceptance is stable.

Local equivalents (a quick check, not proof that Docker CI passed):

```bash
cd backend
python -m pytest
python -m ruff check app scripts tests
python -m ruff format --check app scripts tests
# To include PostgreSQL: export TEST_POSTGRES_URL pointing to a disposable
# PostgreSQL server with CREATE DATABASE permission, then rerun pytest.
cd ../frontend
npm ci
npm run lint -- src tests
npm run lint:operations
npm test -- --run
npm run build
```

## Reset and evidence

Use “Xe tiếp theo”/F9 to clear Station state, and switch lanes only after a request
settles. For a failed gate, retain JSON, session ID, check-in/checkout keys and logs;
inspect whether the session is PARKED, PAYMENT_PENDING or COMPLETED before doing
anything else. Re-running generates new keys and may encounter an old active plate;
finish that acceptance session via the normal UI first. Do not delete audit/ledger
rows to make the next run pass. A clean rerun can use a new dedicated acceptance
building or a restored disposable test environment.

`docker compose down` preserves operational volumes. Never use `down -v` or prune
on a data-preserving environment. CI's destructive cleanup is restricted to its
isolated `visionpark-ci` volumes; unset `COMPOSE_FILE`/`COMPOSE_PROJECT_NAME` after CI.
Keep both gate reports and manually filled A–E evidence in the handover.

## Troubleshooting

| Symptom | Check/action |
| --- | --- |
| Port bind failure | Inspect mapped ports in `.env`, stop the conflicting local service, update both gate URLs. |
| Readiness 503 | Read backend logs, DB health/migrations, model checksums and OCR dependencies; wait for warmup, never substitute mock inference. |
| Frontend healthy but blank | Check `/`, browser console, API base URL and Nginx proxy; health alone does not test browser interactions. |
| 401/403 | Credentials, expired token, building membership/role or mandatory password change. |
| 409 duplicate | An earlier acceptance session is still active; inspect and close through the normal workflow. |
| 422 PRICE_CONTEXT_REQUIRED | Supply the configured customer class and effective CAR/HOURLY tariff. |
| Fee zero | Use a nonzero acceptance tariff with no grace period; preserve free/monthly coverage separately in scenario E. |
| FEE_CHANGED | Review a fresh preview; never silently retry a different amount under the same key. |
| Report/counter mismatch | Stop acceptance; inspect invoice/payment/session IDs and concurrent activity. Do not auto-adjust counters to hide defects. |
| ALPR quality HOLD | Supply licensed labelled media and ready models; system functional results cannot replace this evidence. |
| Race tests skipped | Set TEST_POSTGRES_URL to a disposable PostgreSQL server, or run the CI profile. |
