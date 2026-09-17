# Station

Shell thuộc Người 5 (layout/visual/nav). Player/canvas/throttle/bbox/confirm integration thuộc Người 4 — không duplicate logic ở đây.

- `ScanPage.tsx` — toolbar (lane select, chọn video MP4, demo state), video placeholder, result panel, recent detections (GET /api/v1/detections?limit=5).
- `ScanFullscreenPage.tsx` — overlay toàn màn hình, phím tắt Enter/E/R/Space/Esc, hiển thị plate/confidence/direction.
- `StationPage.tsx` — seam file giữ nguyên ownership Người 4.

Xem thêm `frontend/docs/station.md` và `frontend/docs/alpr.md`.
