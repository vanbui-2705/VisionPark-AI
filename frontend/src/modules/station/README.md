# Station

Shell thuộc Người 5 (layout/visual/nav). Player/canvas/throttle/bbox/confirm integration thuộc Người 4 — không duplicate logic ở đây.

- `StationPage.tsx` — canonical `/station/scan` flow with local MP4, canvas capture,
  bounded sampling, ALPR result/confirmation, IN check-in and OUT checkout.
- `components/VideoPlayer.tsx` — owns video lifecycle, canvas capture and bbox overlay.
- `ImageComparison.tsx` / `ExitSummary.tsx` — ảnh vào/ra, thời gian/phí, CASH và mở cổng.
- `useStationShortcuts.ts` — F2 capture, F4 confirm, F8 cash + gate, F10 free/paid gate, F9 next vehicle.
- `StationPage.tsx` — seam file giữ nguyên ownership Người 4.

Xem thêm `frontend/docs/station.md` và `frontend/docs/alpr.md`.
