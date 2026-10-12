# Backend Core Phase 3 — foundation handoff

Source: Linear project **VisionPark Phase 3 — Bãi đỗ hỗn hợp đa tòa nhà**, checked 12/10/2026.
The new Member M1 issues are VAN-59 through VAN-66 under VAN-54.

## Scope ready for review

| Issue | Implementation |
| --- | --- |
| [VAN-59](https://linear.app/van-bui/issue/VAN-59) | `buildings`, one-to-one `parking_lots`, `user_buildings`; migration `20261012_0011` expands, backfills legacy ownership and enforces NOT NULL with a compatibility default |
| [VAN-60](https://linear.app/van-bui/issue/VAN-60) | Server membership verified at login and every request; signed building claim; shared TenantSession filters reads/aggregates/aliases and guards writes; cross-building IDs/media are inaccessible |
| [VAN-65](https://linear.app/van-bui/issue/VAN-65) | One migration head `20261012_0012`; repeatable one-command seed for two separate demo buildings, each with IN/OUT lanes and Operator/Accountant accounts |

Migration `20261012_0012` scopes lane names, active plates and idempotency keys to a building.
Existing Phase 2 records retain their IDs, passwords, audit payloads and detection links.
The legacy building is `00000000-0000-0000-0000-000000000001`, code `DEFAULT`.
Server defaults preserve writes from the previous application during rollout. New authenticated
writes use the building from the server-resolved account scope, never a client building field.

## Shared integration contract

- Keep using `get_db` and `CurrentUser`/`require_roles`; they bind the same request session to
  the verified building. Do not introduce separate engines/sessions or unfiltered raw SQL.
- `request.state.building_id` and `session.info["building_id"]` contain the verified scope.
- The JWT `building_id` claim must still match a current membership and active building.
  Removing membership or locking the building invalidates access immediately. Existing tokens
  without a building claim work only when the account has one active membership.
- Accounts with no active building or an ambiguous membership cannot log in; multi-building
  selection for non-system accounts is not part of this foundation.
- ADMIN remains the existing system administrator until VAN-62 implements the approved role
  rename/matrix. Other existing roles are filtered to their assigned building. This PR does not
  claim completion of the Phase 3 role matrix.
- Use ORM unit-of-work writes; raw/Core statements and bulk writes are rejected in a scoped
  session. Atomic `User.token_version` revocation is permitted and remains filtered to the building.
- Lane/detection foreign references are checked against the same building before flush.
  Changing ownership of an existing row is rejected. `Session.get` also checks cached objects.
- System administrator check-in writes resolve scope from the selected lane before replay,
  duplicate checks, persistence and audit; aggregate/history reads may span buildings.
- `/api/v1/alpr/media/{key}` requires Bearer authentication and an accessible detection record.
  The frontend loads protected media through the shared client, revokes temporary object URLs
  and discards stale responses. Local Station preview blobs do not make authenticated requests.
- `parking_lots.settings` is a JSON storage foundation. The typed Setting contract, readiness
  checks, pricing integration and UI tabs will be implemented under VAN-63/VAN-66 after the
  authoritative v2.0 document is available.

## Disposable demo bootstrap

Use a local **test/demo database**, configure `DATABASE_URL` and a unique `JWT_SECRET_KEY`,
then set `DEMO_SEED_PASSWORD` to a local value of at least 12 characters. From `backend` run:

```text
python -m app.database.seed_demo
```

This runs migrations and creates DEMO_A/DEMO_B, a parking lot for each, two lanes per building,
and accounts `demo_a_operator`, `demo_a_accountant`, `demo_b_operator`, `demo_b_accountant`.
Running it again does not change existing passwords/settings. Conflicting lane/user identities
raise an error and roll back instead of reassigning operational records. This script is never
called automatically at application startup; the password is supplied through the environment.

## Rollback and review

Final verification on 12/10/2026:

| Check | Result |
| --- | --- |
| Full backend suite, SQLite + PostgreSQL 17.11 | 305 passed, 3 skipped, 1 upstream Starlette/httpx warning |
| PostgreSQL race tests | All three passed; the three skipped cases are their SQLite variants |
| Legacy data upgrade/downgrade and schema/model check | Passed on SQLite/PostgreSQL |
| Cross-building reads/writes, cache, aggregate, alias and private media tests | Passed on SQLite/PostgreSQL |
| One-command clean demo seed, run twice | Passed on SQLite/PostgreSQL |
| Ruff check / format | Passed, 149 Python files |
| pip check | No broken requirements |
| Frontend tests | 75 passed across 20 files |
| Frontend lint / production build | Passed; existing lint and chunking warnings remain |

The databases used for verification were disposable, isolated to this task; the temporary
PostgreSQL servers were stopped after testing. No shared staging/production database was touched.
The dependency install and generated frontend build are scratch artifacts; no package manager
or model files were added to the project. Docker and browser E2E were not run on this host.
Machine-readable summary: `docs/backend-core-phase-3-evidence-2026-10-12.json`.

Upgrade/downgrade tests cover legacy users/roles, lanes, detections, parking transactions,
audit logs, notifications and errors. Downgrade refuses new buildings or cross-building values
that cannot fit the legacy global unique constraints, instead of deleting or merging data.

No teammate approval is inferred from tests. These issues should remain **In Review** until
peer review and the relevant integration gate pass. New teammate migration branches must be
reviewed and merged into the single head when available; they are not blindly imported here.

## Remaining M1 issues

VAN-61 (building/account creation and first-login password change), VAN-62 (new RBAC matrix),
VAN-63 (Setting schema/UI), VAN-64 (complete configuration/account/permission before-after audit)
and VAN-66 (parking readiness and copying settings) are not implemented by this foundation.
They reference **Tài liệu bổ sung nghiệp vụ bãi đỗ xe thông minh hỗn hợp v2.0 (08/10/2026)**,
particularly sections 4.2 and 4.3. That document is absent from the connected Linear documents,
project resources and repository; its link/path has been requested from the user.
