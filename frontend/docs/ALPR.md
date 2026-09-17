# ALPR

Nguồn: `src/modules/alpr/`, `src/api/services.ts` (detectionsApi), `dev/mock-api.mjs`, `GET /health/ready`.

- `GET /health/ready` chứa `alpr.provider` / `alpr.modelVersion` — header hiển thị chấm trạng thái.
- Trang `/admin/alpr` — trạng thái provider, model, ready.
- Lab `/admin/alpr/test` — upload ảnh, chọn lane, chọn scenario (`success | low_confidence | no_plate | error`) gửi kèm header `X-Mock-Scenario` (dev-only). Kết quả 3 tab Visual / JSON / Error, có Copy JSON / Run Again / Clear. Chưa có backend thực thì lab sinh mock client-side và ghi rõ "Development only".

Không overwrite kết quả AI ở UI scan.
