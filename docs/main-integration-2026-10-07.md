# Integration into main — 2026-10-07

Real-data demo implementation was committed as `303b246` on van-dev and
integrated with main `7fd7497`. Conflict resolution retains real-only YOLO/OCR,
canonical final-capture confirmation, database preferences/notifications,
four-role authorization, safe migrations and existing volume names.

The incoming CSS additions and audit pagination UI are retained. Audit pagination
now calls the real paginated API with limit/offset; resource/search filtering is
handled in SQL. Audit details retain AI/final plate, source, actor and timestamp.
Other conflicting pages retain the tested database workflows and localization;
the older mock fallbacks and incompatible pagination assumptions are removed.

Verification on the merged code:

- Frontend: 61 tests passed; audit regression 7 passed after localization;
  build passed and lint passed with existing React warnings.
- Backend related workflows/core/Station: 27 passed, 3 SQLite skips for PostgreSQL
  races. Final workflow suite including >200-row audit filtering/pagination:
  9 passed. Ruff passed.
- OpenSpec strict validation passed; quality gate remains open as documented.

Counts from overlapping test groups must not be summed. No application deployment,
database migration or Docker volume operation was performed during Git integration.
The earlier review report describes main 7fd7497 before these fixes, not this merge.
