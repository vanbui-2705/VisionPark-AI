# Backend Core Phase 3 — Member 2 handoff

Owner: Đinh Túy / Backend Core, branch `dqt_core`. Checked 12/10/2026.
Linear assigns VAN-59–66 under VAN-54 to this owner. Source: business specification v2.0
dated 08/10/2026, sections 4.2, 4.3 and 5.2. The user's latest instruction limits this delivery
to backend work. New Setting/account frontend implementation is excluded from these commits.

| Issue | Backend implementation |
| --- | --- |
| VAN-59 | Buildings, one parking lot per building, memberships; additive migration, default-building backfill, preserved legacy data |
| VAN-60 | Verified JWT membership, shared TenantSession isolation, guarded writes and authenticated media |
| VAN-61 | Building/account provisioning, generated temporary password, first-login restriction, disabled public registration |
| VAN-62 | Four canonical roles and business permissions; building scope and role-change audit |
| VAN-63 | Typed Setting schema and APIs for A/B/C/G/H/I; capacity/quota/occupancy and revision validation. **Frontend frame/tabs remain pending** |
| VAN-64 | Atomic before/after audit for Setting, lanes, accounts, roles and building state |
| VAN-65 | One migration head `20261012_0013`; repeatable two-building seed with admins/operators/accountants |
| VAN-66 | Missing-configuration readiness guard, CLOSED entry blocking, system-only revision-checked configuration copy |

Full contracts, API payloads, RBAC matrix and integration instructions:
[Backend Core Phase 3 API](backend-core-phase-3-api.md).

## Verification

- Backend SQLite + PostgreSQL 17.11: **325 passed, 3 skipped**, 356.10 seconds.
  Three SQLite race variants are skipped; all three PostgreSQL variants pass.
- Role/foundation migration upgrade and downgrade preserve existing identities and data.
- Provisioning, password changes, token revocation, isolation, Setting validation, audit,
  readiness, copy, per-building AI threshold and repeatable empty-database seed pass.
- Ruff check/format: 163 files pass. `pip check` and `git diff --check` pass.
- One upstream Starlette/httpx deprecation warning remains.
- Tests use disposable databases; the temporary PostgreSQL server was stopped.

Machine-readable evidence: [12/10/2026 evidence](backend-core-phase-3-evidence-2026-10-12.json).
No shared database was migrated. Docker full stack and browser E2E were not run locally.

## Integration and review gate

Canonical roles are SYSTEM_ADMIN, BUILDING_ADMIN, OPERATOR and ACCOUNTANT. The frontend owner
must update its role mapping and handle PASSWORD_CHANGE_REQUIRED before deployment.
VAN-63 stays In Progress because its frontend frame/tabs are not included in this delivery.
The other backend tasks are ready for review; no peer approval or Done status is inferred.

M4 registers `app.state.effective_pricing` using real building-owned pricing versions. Without
that provider and mandatory lot configuration, production entry correctly remains blocked.
This PR does not implement M4 tariffs/tickets/payments, M3 counters/checkout/lifecycle, or
M2/M5 model training/fire incidents/dashboard. Shared adapters and migrations require owner review.
New teammate migration branches must be reviewed before merging into the single current head.
