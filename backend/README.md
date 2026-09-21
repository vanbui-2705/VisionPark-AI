# VisionPark Backend Core

Backend Core owns FastAPI, settings/CORS, PostgreSQL sessions, Alembic,
User/Role identity, Argon2id/JWT, RBAC, errors, correlation IDs and health.

## Local setup (Windows PowerShell)

Prerequisites: Python 3.11+ and a running PostgreSQL server. This revision was
verified with Python 3.13 and PostgreSQL 17.11. Create a dedicated local database
and a user that can migrate it; set their connection URL in `.env`.
Run from `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env`: set `DATABASE_URL`, a unique `JWT_SECRET_KEY` of at least 32 characters,
`SEED_ADMIN_PASSWORD` and `SEED_OPERATOR_PASSWORD`. Keep `ALPR_PROVIDER=mock` and
`AUTO_SEED=true` for the demo. The example URL uses port 5432; change it if your
local PostgreSQL uses a different port. Never use a shared/production DB for tests.

```powershell
.\.venv\Scripts\python.exe -m app.database.bootstrap
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Bootstrap runs `alembic upgrade head` and then idempotent demo seed. Run it again
safely: there remain four roles, two demo users (`admin`/`operator`) and two lanes.
The server listens on port 8000; Swagger is `/docs`. Both Alembic CLI and the app
read environment variables and `.env` consistently. Explicit test URLs override
that configuration via Alembic `config.attributes["database_url"]`.

On Linux/macOS use `.venv/bin/python` and `cp .env.example .env`.
Docker Compose for the complete frontend/backend stack is outside this change.

## Authentication and authorization

| Endpoint | Access |
| --- | --- |
| `GET /health/live`, `GET /health/ready` | Public |
| `POST /api/v1/auth/login` | Public; JSON `username` and `password` |
| `GET /api/v1/auth/me` | Active authenticated user |
| Lane list, active list, detail | Active authenticated user |
| Lane create/update/deactivate | ADMIN |
| `POST /api/v1/alpr/detections` | ADMIN or OPERATOR |

Login returns an access token and public user data. Use `Authorization: Bearer
<token>`. `/auth/me` never returns password hashes. Domain modules must use
`CurrentUser` or `require_roles`, not their own JWT decoder. User CRUD, registration,
history and confirmation are not implemented by this change.

Detection accepts multipart `image` (JPEG/PNG) and a UUID `lane_id` from Lane API.
The current response names remain `raw_plate`, `normalized_plate`, `bbox`,
`confidence`, `latency_ms`, `model_version`; a missing plate retains the existing
zero bbox convention. Broader ALPR contract changes require a separate review.

All handled HTTP/validation/database errors, including route 404/405 and unexpected
500, use `{code, message, details, correlation_id}`. `X-Correlation-ID` matches the
body and is exposed to browser clients for ordinary CORS responses. Credentials
and JWTs are not written by request logging. Keep `DEBUG=false` outside debugging.

## ALPR and database integration

- One runtime on `app.state.alpr_runtime` serves both detection and readiness.
- `mock` is deterministic and explicitly reports `mock-alpr-0.1.0`; it does not
  recognize real plates. Other providers remain `not_ready` (503).
- ONNX source still has placeholder output decoding. The optional `[onnx]` extra
  supplies its library, but installing it does not activate a real provider.
- `/api/v1/alpr/health/*` are aliases of the shared health handlers; ready checks
  both DB and runtime and never claims DB readiness without checking it.
- `get_db` provides one request session. The DI factory passes it to both adapters
  under `app/integrations/persistence/`; there is no `SessionLocal` compatibility
  engine. AI ports remain free of ORM imports.
- Detection persistence uses UUID lane IDs. A failed database write rolls back
  through `get_db` and removes the image created by that attempt.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
# Against the running local server and .env demo account:
.\.venv\Scripts\python.exe scripts/smoke_core.py
```

To also run database-dependent tests on real PostgreSQL:

```powershell
$env:TEST_POSTGRES_URL='postgresql+psycopg://YOUR_TEST_USER:YOUR_PASSWORD@127.0.0.1:5432/postgres'
.\.venv\Scripts\python.exe -m pytest
Remove-Item Env:TEST_POSTGRES_URL
```

The test user must have `CREATEDB`. Tests create and drop their own UUID-named
`vp_test_*` databases; they do not migrate the database named in that connection URL.
By default only SQLite runs. No model weights are downloaded.

Run destructive rollback checks only on a disposable local test database:
`python -m alembic downgrade base`, then `python -m app.database.bootstrap`.
`python -m alembic check` verifies that migration head matches ORM metadata.
See [handoff](../docs/backend-core-handoff.md) for evidence and migration notes.
