# Backend

FastAPI + PostgreSQL, Alembic migration trước startup. API routes và DTO được
mô tả trong API.md và OpenAPI `/docs`.

Lanes được đọc bởi user đăng nhập, ghi bởi ADMIN. Users/roles API yêu cầu ADMIN.
ALPR/detection/parking/audit yêu cầu ADMIN hoặc OPERATOR. Auth giữ role thật.
Preview không persist; final lưu metadata/ảnh. Check-in lưu PARKED và audit,
chống trùng active plate và hỗ trợ idempotency. Confirm check-in qua canonical
ALPR confirm endpoint hoặc nhập tay qua parking/check-in.

Real ALPR tùy chọn, mock mặc định. Readiness phản ánh database + runtime;
mock ready không chứng minh recognition accuracy. ALPR không mở barrier.
