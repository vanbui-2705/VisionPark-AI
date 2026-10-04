# Station

Shell thuộc Người 5 (layout/visual/nav). Player/canvas/throttle/bbox/confirm integration thuộc Người 4 — không duplicate logic ở đây.

- `StationPage.tsx` — canonical `/station/scan` flow with local MP4, canvas capture,
  bounded sampling, ALPR result/confirmation and check-in history.
- `components/VideoPlayer.tsx` — owns video lifecycle, canvas capture and bbox overlay.
- `ScanFullscreenPage.tsx` — overlay toàn màn hình, phím tắt Enter/E/R/Space/Esc, hiển thị plate/confidence/direction.
- `StationPage.tsx` — seam file giữ nguyên ownership Người 4.

Xem thêm `frontend/docs/station.md` và `frontend/docs/alpr.md`.
