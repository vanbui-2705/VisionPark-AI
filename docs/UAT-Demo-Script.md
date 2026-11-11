# VisionPark System Acceptance Script — FILE_UPLOAD

Tài liệu này nghiệm thu hệ thống VisionPark chạy thật với ảnh JPEG/PNG và video MP4.
Frontend trích frame từ MP4 rồi gửi byte ảnh vào real ALPR provider. `LIVE_CAMERA/RTSP`
chưa tích hợp và không nằm trong kết luận functional acceptance hiện tại.

## 1. Quy tắc kết luận

- Không ghi sẵn `PASS`. Người chạy điền kết quả và đường dẫn evidence sau khi thực hiện.
- Functional status và ALPR quality status là hai kết luận độc lập.
- Functional acceptance dùng hệ thống, PostgreSQL và real ALPR provider đang triển khai.
- Ground truth chỉ dùng để đối chiếu sau inference, không được dùng làm input/fallback.
- Barrier business event và ACK của controller vật lý phải được báo cáo riêng.
- Thiếu stack, credentials hoặc acceptance media trả `HOLD`; lỗi chức năng trả `FAIL`.

Exit code của hai gate:

- `0`: `PASS`.
- `1`: `FAIL`.
- `2`: `HOLD`.

## 2. Preflight

Ghi lại trước khi chạy:

| Trường | Giá trị |
| --- | --- |
| Commit SHA | |
| Ngày/giờ | |
| Máy/OS | |
| Backend URL | |
| Frontend URL | |
| Database | PostgreSQL / khác |
| ALPR provider | |
| Model version | |
| Input mode | `FILE_UPLOAD` |
| Camera live/RTSP | `NOT_INTEGRATED` |
| Barrier controller | `CONNECTED` / `NOT_INTEGRATED` / `UNVERIFIED` |

Chạy:

```powershell
cd backend
py -3 -m pytest tests
py -3 -m ruff check app scripts tests
py -3 -m ruff format --check app scripts tests
py -3 scripts/verify_model_bundle.py

$env:SEED_OPERATOR_PASSWORD = '<local operator password>'
py -3 scripts/system_gate.py --image <path-to-image> --video <path-to-mp4>
py -3 scripts/release_gate.py --dataset datasets/phase2-release.json

cd ../frontend
npm test -- --run
npm run lint
npm run build
```

Kiểm tra thêm:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Không chạy `docker compose down -v` trên môi trường cần giữ dữ liệu.

## 3. Acceptance media

Mỗi file phải có manifest gồm source, usage rights, SHA-256 và expected scenario.

| Media | Mục đích | SHA-256 hợp lệ | Kết quả |
| --- | --- | --- | --- |
| Ảnh biển rõ | Workflow thành công | | |
| Ảnh confidence thấp | Operator xác nhận/sửa | | |
| Ảnh không có biển | Manual fallback | | |
| MP4 | Frontend trích frame và inference | | |
| Ảnh xe vào/ra | Đối chiếu checkout | | |
| Xe vé tháng | Entitlement/phí 0 | | |

## 4. Kịch bản A — Xe vãng lai và CASH

1. Đăng nhập tài khoản có quyền `OPERATOR`.
2. Chọn một làn `IN` active.
3. Upload ảnh hoặc MP4 từ acceptance manifest.
4. Xác nhận response dùng real provider và đúng model version.
5. Xác nhận/sửa biển số nếu cần rồi thực hiện check-in.
6. Kiểm tra transaction ở trạng thái `PARKED` và counter tăng đúng một lần.
7. Chuyển sang làn `OUT`, tìm đúng phiên theo biển số hoặc session.
8. Preview phí và ghi lại `expected_fee`.
9. Xác nhận đã thu đủ `CASH`.
10. Kiểm tra checkout hoàn tất và counter giảm đúng một lần.
11. Kiểm tra trực tiếp database/API:
    - đúng một `ParkingTransaction`;
    - đúng một `Invoice`;
    - đúng một `Payment` trạng thái `PAID`;
    - amount bằng phí đã xác nhận;
    - dashboard/report tăng một lượt ra và đúng doanh thu;
    - audit/lifecycle lưu actor và hành động.
12. Gửi lại cùng idempotency key và payload; xác nhận không tạo bản ghi trùng.

Kết quả: `PASS / FAIL / HOLD`

Evidence:

## 5. Kịch bản B — Confidence thấp và operator correction

1. Upload acceptance media có confidence thấp.
2. Xác nhận UI yêu cầu operator kiểm tra, không tự hoàn tất sai biển số.
3. Sửa biển số và nhập lý do nếu contract yêu cầu.
4. Hoàn tất check-in.
5. Kiểm tra audit lưu kết quả AI, kết quả cuối và actor.

Kết quả: `PASS / FAIL / HOLD`

Evidence:

## 6. Kịch bản C — Duplicate protection

1. Dùng lại biển số đang có transaction `PARKED`.
2. Thực hiện check-in lần hai.
3. Xác nhận API trả lỗi duplicate có mã rõ ràng.
4. Kiểm tra không có transaction, counter event hoặc barrier event mới.

Kết quả: `PASS / FAIL / HOLD`

Evidence:

## 7. Kịch bản D — Manual fallback

1. Upload ảnh không có biển hoặc kiểm tra nhánh real provider unavailable.
2. Xác nhận Station cung cấp đường nhập biển số thủ công.
3. Nhập biển số và lý do.
4. Hoàn tất check-in.
5. Kiểm tra source/audit thể hiện manual entry, actor và ảnh gốc nếu có.

Kết quả: `PASS / FAIL / HOLD`

Evidence:

## 8. Kịch bản E — Vé tháng/phí 0

1. Dùng xe có subscription còn hạn.
2. Check-in và xác nhận entitlement đúng building/zone.
3. Checkout và xác nhận phí bằng 0 theo price snapshot/policy.
4. Kiểm tra transaction hoàn tất, counter giảm và lượt ra được ghi nhận.
5. Kiểm tra không tạo doanh thu hoặc `Payment CASH` giả.

Kết quả: `PASS / FAIL / HOLD`

Evidence:

## 9. Kiểm tra input mode

### JPEG/PNG

- API nhận đúng multipart payload.
- Response ghi real provider/model version.
- Preview không persist ngoài contract.
- Final/confirm persist đúng detection, media và transaction.

### MP4

- Frontend mở file MP4 cục bộ.
- Frame được trích tại thời điểm người dùng chọn.
- Request gửi `input_kind=VIDEO_FRAME` và `video_time_ms`.
- Backend nhận byte ảnh frame và chạy real ALPR provider.
- Không mô tả MP4 là camera live.

## 10. Barrier status

Nếu có controller vật lý, lưu command, ACK, latency và lỗi adapter. Nếu chưa có controller,
chỉ kết luận barrier business event đã được lưu; trạng thái physical controller là
`NOT_INTEGRATED` hoặc `UNVERIFIED`. Không dùng `barrier_opened=true` của business response làm
bằng chứng ACK vật lý.

## 11. Kết luận

| Hạng mục | Kết quả | Evidence/Blocker |
| --- | --- | --- |
| Backend/frontend/PostgreSQL | | |
| JPEG/PNG FILE_UPLOAD | | |
| MP4 FILE_UPLOAD | | |
| CASH/Invoice/Payment | | |
| Counter/dashboard/report/audit | | |
| Retry/idempotency | | |
| Manual fallback | | |
| Monthly/phí 0 | | |
| ALPR Quality Gate | | |
| LIVE_CAMERA/RTSP | `NOT_INTEGRATED` | Ngoài phạm vi hiện tại |
| Physical barrier | | |

Chỉ ghi hệ thống `READY` khi toàn bộ functional scope có evidence và không còn lỗi
Critical/High. Quality Gate được báo cáo riêng bằng `PASS`, `FAIL` hoặc `HOLD`.
