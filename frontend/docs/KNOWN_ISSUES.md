# Known Issues — 13/11/2026

- YOLO + OCR và E2E Ảnh/Video thật đã chạy trên Docker với video miLPR người dùng cung cấp.
- Bộ đánh giá hiện chỉ gồm hai xe trong một video demo có overlay; chưa đủ để kết luận độ chính xác tổng quát.
- Benchmark gần nhất: đúng toàn bộ biển số 8/10 ảnh có biển; warm p50 1,30 giây, p95 3,03 giây trên CPU. Chưa đạt mục tiêu dưới 1 giây. Operator tiếp tục xác nhận kết quả.
- Camera RTSP và barrier vật lý chưa được hỗ trợ. Check-out, phí/payment, vé tháng,
  khu vực đỗ và access rules đã có luồng backend/frontend; barrier vẫn là sự kiện mô phỏng.
- Profile, đổi mật khẩu, thu hồi phiên, preferences, notifications và error center đã nối database.
- Gate chất lượng tổng thể vẫn mở. Evidence mới nằm trong docs/phase-2-evidence/completion-*.json.
- `backend/BENCHMARK_REPORT.md` đã sửa các ô đánh giá sai: vehicle recall, plate recall,
  tỷ lệ sửa tay và fire latency đều KHÔNG ĐẠT theo chính ngưỡng của báo cáo.

Đã sửa: token/base URL Station, mock check-in frontend, active/is_active,
confirmation payload/route, detection detail, users/roles API, health status,
Docker phục vụ bản cũ và dashboard đếm trên 5 bản ghi.
