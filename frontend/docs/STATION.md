# Station

Nguồn: `src/modules/station/` (`ScanPage`, `ScanFullscreenPage`, `StationPage`), `src/api/services.ts`.

- Shell thuộc Người 5 (layout/visual/nav). Player/canvas/throttle/bbox/confirm thuộc Người 4 — không duplicate.
- `ScanPage` — toolbar (lane select, chọn video MP4, demo state), video placeholder, result panel, recent detections (`GET /api/v1/detections?limit=5`).
- `ScanFullscreenPage` — overlay toàn màn hình, phím tắt Enter/E/R/Space/Esc, hiển thị plate/confidence/direction lớn.
- Confirm `POST /api/v1/alpr/detections/{id}/confirmation`; lỗi thì toast "API pending" nhưng vẫn chuyển UI state (không fake success).
