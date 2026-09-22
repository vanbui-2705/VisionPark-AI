# VisionPark Backend Core

Backend Core is the shared FastAPI foundation for Phase 1. It owns configuration,
PostgreSQL sessions, Alembic, User/Role identity, JWT authentication, reusable RBAC,
request correlation, error responses, and health checks.

## Local setup

Use Python 3.11 or newer from the `backend` directory:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
alembic upgrade head
python -m app.database.seed
uvicorn app.main:app --reload
```

Set strong local values for `JWT_SECRET_KEY`, `SEED_ADMIN_PASSWORD`, and
`SEED_OPERATOR_PASSWORD` in `.env`. The seed command is idempotent: running it again
does not duplicate roles or users.

## API contract

- `GET /health/live`: process liveness; it never checks dependencies.
- `GET /health/ready`: checks database and the ALPR readiness adapter.
- `POST /api/v1/auth/login`: JSON body with `username` and `password`; returns an
  HS256 JWT access token and public user data.
- `GET /api/v1/auth/me`: returns the bearer token's current active user.

Every handled error uses this shape:

```json
{
  "code": "FORBIDDEN",
  "message": "You do not have permission to perform this action.",
  "details": {},
  "correlation_id": "7da831eb-0b36-4a25-bb03-9efc8fe45574"
}
```

The `X-Correlation-ID` response header contains the same request identifier.

## Protecting another module

Use the shared dependencies instead of decoding tokens inside endpoints:

```python
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName


def list_lanes(current_user: CurrentUser):
    ...


def create_lane(
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    ...


def create_detection(
    current_user: Annotated[
        User,
        Depends(require_roles(RoleName.ADMIN, RoleName.OPERATOR)),
    ],
):
    ...
```

Lane listing requires any authenticated user. Lane mutation requires `ADMIN`.
Detection and confirmation require `ADMIN` or `OPERATOR`.

## ALPR readiness handoff

Backend Core intentionally depends on the `ALPRReadinessProbe` protocol, not on a
concrete ONNX or mock implementation. The ALPR owner wires an object with a
`readiness() -> ReadinessStatus` method to `app.state.alpr_readiness_probe`. Existing
`ALPRRuntime.is_ready()` implementations can be wrapped with `RuntimeALPRProbe`.
Until that integration happens,
`/health/ready` returns `503` and explicitly reports the configured `mock` provider
as `not_ready`; it never claims that inference is available when it is not.

## Verification

```bash
pytest
ruff check app/core app/database app/modules app/api/router.py \
  app/api/endpoints/health.py app/main.py tests
```

Migration rollback can be checked separately:

```bash
alembic downgrade base
alembic upgrade head
```

## Docker

Build the backend image from the repository root:

```bash
docker build -t visionpark-backend ./backend
```

Run the API on port `8000`:

```bash
docker run --rm -p 8000:8000 visionpark-backend
```

When PostgreSQL runs on the host machine, pass a container-accessible database
URL instead of `localhost`:

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg://visionpark:visionpark@host.docker.internal:5432/visionpark \
  visionpark-backend
```

The container healthcheck calls `/health/live`. `/health/ready` additionally
requires PostgreSQL and an initialized ALPR readiness provider.
