# Database

Frontend không sở hữu DB; đây là tham chiếu cho backend (Phase 1).

- Bảng gợi ý: `users`, `lanes`, `detections`, `audit_logs`, `roles`/`permissions`.
- Lanes: `id`, `name` (unique), `direction` (IN/OUT), `video_source`, `active`, `created_at`.
- Detections: `id`, `lane_id`, `ai_plate`, `normalized_plate`, `final_plate`, `confidence`, `status` (NEEDS_CONFIRMATION/CONFIRMED/CORRECTED), `bbox`, `image_url`, `created_at`.
- Audit: `id`, `actor`, `action`, `resource`, `resource_id`, `before`, `after`, `created_at`.


Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.

## M4 pricing foundation

Migration `20261012_0014` (sau nền tảng tòa nhà `0011`–`0013`) adds `customer_classes`, `class_quotas`, `ticket_products`,
`pricing_versions`, `pricing_rules`, `vehicles`, `subscriptions`, `guest_invites`,
`invoices`, and `payments`. It also adds nullable `parking_transactions.price_snapshot`
so existing Phase 2 transactions remain valid. Money is stored as integer VND.

M4 derives the building from the authenticated session and the M1 membership. The check-in row captures its price rule/version as JSON. Pricing
snapshot also records the registered day/month pass expiry when one applies; invoices
charge only overage after that expiry. Pricing versions are append-only; invoices have
one row per transaction, and `provider_ref` plus
`invoice_id`/`idempotency_key` protect payment callbacks and retries.
