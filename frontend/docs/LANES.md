# Lanes

Nguồn: `src/modules/lanes/` (`LaneListPage`, `LaneForm`, `LanePages`), `src/api/lanesApi.ts`, `dev/mock-api.mjs`.

- Routes: `/admin/lanes` (list), `/admin/lanes/new` (create), `/admin/lanes/:id` (detail), `/admin/lanes/:id/edit` (edit). Không có DELETE (Phase 1).
- Form: `name`, `direction` (IN/OUT), `video_source`, `active`. Validate trống + trùng tên (`DUPLICATE_LANE_NAME`).
- Detail hiển thị metadata + audit. List có filter/search + pagination. Guard `useUnsavedGuard` khi dirty.
