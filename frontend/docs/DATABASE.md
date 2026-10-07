# Database

Frontend không sở hữu DB; đây là tham chiếu cho backend (Phase 1).

- Bảng gợi ý: `users`, `lanes`, `detections`, `audit_logs`, `roles`/`permissions`.
- Lanes: `id`, `name` (unique), `direction` (IN/OUT), `video_source`, `active`, `created_at`.
- Detections: `id`, `lane_id`, `ai_plate`, `normalized_plate`, `final_plate`, `confidence`, `status` (NEEDS_CONFIRMATION/CONFIRMED/CORRECTED), `bbox`, `image_url`, `created_at`.
- Audit: `id`, `actor`, `action`, `resource`, `resource_id`, `before`, `after`, `created_at`.


Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.
