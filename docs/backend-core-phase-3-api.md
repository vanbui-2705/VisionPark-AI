# Backend Core — Phase 3 API handoff

Owner: Đinh Túy / Member 2, branch `dqt_core`. Linear: VAN-54, VAN-59–66.
Business source: *VisionPark — Tài liệu bổ sung và cải thiện nghiệp vụ bãi đỗ xe hỗn hợp*,
v2.0 dated 08/10/2026, sections 4.2, 4.3 and 5.2.
The current delivery is backend implementation and contracts. The Setting UI portion of
VAN-63 remains to be integrated by the frontend owner; it is not claimed complete here.

## Accounts and building scope

`ADMIN` becomes `SYSTEM_ADMIN`; `TECHNICIAN` becomes `BUILDING_ADMIN`. Role IDs and existing
password hashes remain unchanged. The other roles are `OPERATOR` and `ACCOUNTANT`.
Clients must support these canonical role strings before deploying this backend version.
The existing frontend role mapping requires an integration update.

Every request uses `CurrentUser` and the shared `get_db` dependency. Membership is checked
against the database at login and on every request. Non-system accounts require exactly one
active building. Request JSON/query parameters cannot choose their building. Only authenticated
`SYSTEM_ADMIN` can select a building for overview, provisioning and copy operations.

| API, under `/api/v1` | Permission | Behavior |
| --- | --- | --- |
| `GET /buildings` | Authenticated | Assigned building; SYSTEM_ADMIN sees all |
| `POST /buildings` | SYSTEM_ADMIN | `{code,name,address,timezone}`; creates one parking lot and default settings atomically |
| `PATCH /buildings/{id}` | SYSTEM_ADMIN | `{is_active}`; locking immediately prevents tenant access |
| `POST /buildings/{id}/admins` | SYSTEM_ADMIN | `{username,display_name,email?}`; returns public user and generated temporary password once, `Cache-Control: no-store` |
| `POST /users` | SYSTEM_ADMIN / BUILDING_ADMIN | Building admin creates OPERATOR/ACCOUNTANT in the server scope; system admin may supply a target `building_id` |
| `PATCH /users/{id}` | SYSTEM_ADMIN / BUILDING_ADMIN | Public profile, active state, role or password; building admin manages staff only; access changes revoke tokens |
| `GET /auth/me` | Authenticated | Includes canonical `role` and `must_change_password` |
| `POST /auth/change-password` | Authenticated | `{current_password,new_password}`; clears temporary-password restriction and revokes existing sessions |

Temporary accounts can use only `auth/me`, `auth/change-password` and `auth/logout` until the
password changes. Reusing the temporary password is rejected. Admin password resets also require
a subsequent password change. Public registration remains disabled even if its legacy environment
flag is enabled. No password/hash is written to audit JSON.

## Business permissions

Domain routers can use `require_permissions(...)` from `modules/auth/dependencies.py`.
The backend registry is `modules/users/permissions.py`; domain owners must enforce it at their
new endpoints, alongside building filtering. A permission registry does not implement the
barrier, incident or pricing workflows themselves.

| Permission | SYSTEM_ADMIN | BUILDING_ADMIN | OPERATOR | ACCOUNTANT |
| --- | --- | --- | --- | --- |
| `override_barrier` | — | Yes | Yes | — |
| `manage_incident` | — | Yes | — | — |
| `view_revenue` | Yes | Yes | — | Yes |
| `manage_pricing` | — | Yes | — | — |
| `manage_settings` | — | Yes | — | — |
| `copy_settings` | Yes | — | — | — |

## Typed Setting, groups A/B/C/G/H/I

`GET /settings/lot` returns `{building_id,revision,settings,readiness}`. A system administrator
must pass `?building_id=<uuid>`. Other roles use their server scope and cannot pass this parameter.
`PUT /settings/lot` accepts `{revision,settings}` from BUILDING_ADMIN only. Schema definitions
are published in OpenAPI and `backend/app/modules/lot_settings/schemas.py`.

Configuration is stored as validated JSON in `parking_lots.settings`, with `schema_version: 1`.
This M1 implementation does not create M4's ticket products/pricing tables or M3's counters.

| Group | Key / API | Fields |
| --- | --- | --- |
| A | `information` | name, address, IANA timezone, OPEN/CLOSED/MAINTENANCE, operating_hours (`weekday` 0=Monday, `start`, `end` local time) |
| B | `capacities` | CAR/MOTORBIKE/BICYCLE: physical_capacity, safe_capacity, nearly_full_threshold and full_threshold in percent |
| C | `quotas` | Same three types: residents, employees, visitors |
| G | Existing `/lanes/` APIs | IN/OUT, active, video_source, allowed_vehicle_types, nullable camera/barrier identifiers; only BUILDING_ADMIN writes |
| H | `ai` | vehicle_confidence, plate_confidence (0–1 or null when unconfigured) |
| I | `fire` | fire/smoke confidence, confirmation_frames, confirmation_window_seconds, alert_recipients, areas, escape_exits |

Rules:

- All three vehicle buckets must exist. Integer capacities/quotas cannot be negative.
- Safe capacity cannot exceed physical capacity or fall below currently PARKED sessions.
- Quotas cannot sum above safe capacity. Nearly-full threshold cannot exceed full threshold.
- Alert-recipient UUIDs must belong to the target building. Unknown extra fields are rejected.
- Empty operating_hours means 24/7. Windows cannot overlap; overnight hours must be split.
- Revision conflicts return `409 SETTINGS_CONFLICT`. Row locks serialize PostgreSQL updates
  and entry checks; optimistic version checking also prevents lost Setting writes.
- Group I is edited only by BUILDING_ADMIN. M5 consumes the schema to implement incident rules.

The current Phase 2 session schema has no vehicle_type, so legacy PARKED sessions count as CAR.
`occupied_by_type()` automatically groups by vehicle_type once M3 adds that mapped column;
unknown types conservatively count in every bucket. M3 should reuse the parking-lot lock when
implementing conditional counter increments and adjustments.

The existing plate pipeline applies H before returning preview or recording a new detection.
A missing plate threshold, low confidence, missing plate/bbox or quality flags require review.
Persisted capture retries retain their original result. Vehicle/fire policies remain with M2/M5.

## Readiness and copy

New entry requires an active building, OPEN state, operating hours, positive safe capacity,
active IN and OUT lanes, and effective pricing. Missing requirements produce
`409 LOT_NOT_READY` with machine-readable `details.missing` (also returned by GET Setting).
Existing successful idempotent retries remain valid after the lot closes. This guard does not
implement or restrict the future checkout workflow.

M4 supplies `app.state.effective_pricing`, a `PricingChecker` with signature
`(Session, building_id: UUID, at: datetime) -> bool`. It must read actual, building-owned,
committed pricing versions at the supplied UTC instant. An absent provider returns false;
there is no production fake tariff or checkbox that makes a price effective. Test fixtures
explicitly install a pricing test double. **Production entry remains blocked until M4 integrates
its provider and the building manager completes the mandatory settings.**

`POST /buildings/{source_id}/copy-settings` (SYSTEM_ADMIN) accepts:

```json
{
  "target_building_id": "<uuid>",
  "source_revision": 0,
  "target_revision": 0
}
```

This copies capacities, quotas and AI thresholds. It preserves target information/operating hours,
PCCC contacts/areas/exits and physical lane/camera/barrier identities. Target occupancy and revisions
are validated, reciprocal copies lock rows in consistent order, and the target-building audit
records the source building. Prices/tickets remain M4-owned and are not copied by this API.

## Audit and migrations

Creation, locking, role changes and every Setting/lane mutation commit their before/after audit
in the same transaction as the change. Audit includes actor, timestamp and target building.
Lane deactivation writes one complete before/after event; repositories no longer commit before audit.

The single migration head is `20261012_0013`. It adds only defaulted/nullable fields and renames
role values, preserving IDs/hashes. Downgrade restores role names. Earlier foundation downgrades
refuse to discard new-building data or cross-building uniqueness.

`DEMO_SEED_PASSWORD` (12+ characters), then `python -m app.database.seed_demo`, provisions two
repeatable demo buildings with IN/OUT lanes, BUILDING_ADMIN, OPERATOR and ACCOUNTANT accounts.
Building admins must change the supplied password. Re-running never resets passwords or settings.
Demo lots initially remain unconfigured; the script does not fabricate effective pricing.

Before deployment, frontend integration must consume the new roles, handle PASSWORD_CHANGE_REQUIRED,
and connect its Setting tabs. M4 integrates pricing readiness; M3/M5 connect the published schema
and permission hooks. Review of shared domain adapters/migrations is required before merge.
