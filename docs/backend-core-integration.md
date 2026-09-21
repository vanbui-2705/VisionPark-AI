# Backend Core integration contract

## Shared ownership

Backend Core owns application creation, `/api/v1` router composition, identity,
security, database sessions, global errors, and health endpoints. Domain owners keep
business rules in their own modules and expose one router for composition.

Add a domain router in `app/api/v1/router.py`:

```python
api_router.include_router(lane_router, prefix="/lanes", tags=["lanes"])
```

Do not create a second FastAPI application, SQLAlchemy engine, JWT decoder, or error
format in a domain module.

## Dependencies for other Phase 1 owners

- Authenticated user: `app.modules.auth.dependencies.CurrentUser`
- Role authorization: `app.modules.auth.dependencies.require_roles`
- Request database session: `app.database.session.get_db`
- ORM import registry for Alembic: `app.database.models`
- Stable ALPR readiness boundary: `app.core.readiness.ALPRReadinessProbe`

When another owner adds an ORM model, import it from `app.database.models` and create
a new Alembic revision. Never modify the applied identity revision to add domain
tables.

## Authorization matrix

| Capability | ADMIN | OPERATOR |
| --- | --- | --- |
| Health and login | Public | Public |
| Current user and Lane list | Yes | Yes |
| Lane create/update/inactivate | Yes | No |
| Detection, history, confirmation | Yes | Yes |

The frontend may hide controls, but the endpoint must still use the corresponding
Backend Core dependency.


## Verified wiring (2026-09-21, dqt_core)

`get_alpr_service` injects the same `get_db` session into concrete adapters under
`app.integrations.persistence`. Do not import `SessionLocal` or instantiate an
engine inside an adapter. Detection and health share `app.state.alpr_runtime`.
The mock provider reports `mock-alpr-0.1.0`; unsupported providers are not ready.
See [handoff](backend-core-handoff.md) for PostgreSQL migration evidence and
[Users API proposal](users-api-scope-proposal.md) for pending scope decisions.
