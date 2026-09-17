# Database

Frontend không sở hữu DB; đây là tham chiếu cho backend (Phase 1).

- Bảng gợi ý: `users`, `lanes`, `detections`, `audit_logs`, `roles`/`permissions`.
- Lanes: `id`, `name` (unique), `direction` (IN/OUT), `video_source`, `active`, `created_at`.
- Detections: `id`, `lane_id`, `ai_plate`, `normalized_plate`, `final_plate`, `confidence`, `status` (NEEDS_CONFIRMATION/CONFIRMED/CORRECTED), `bbox`, `image_url`, `created_at`.
- Audit: `id`, `actor`, `action`, `resource`, `resource_id`, `before`, `after`, `created_at`.

Mock hiện tại: in-memory trong `dev/mock-api.mjs`.
