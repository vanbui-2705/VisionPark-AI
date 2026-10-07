# ALPR

Provider được chọn trên backend qua ALPR_PROVIDER. Mock mặc định trả kết quả
mô phỏng có nhãn; frontend luôn gọi API thật.

`/admin/alpr` đọc `/health/ready`: status, provider, version, ocr_enabled.
`/admin/alpr/test` gửi JPEG/PNG cùng UUID lane từ API ở preview/persist=false;
hiển thị output thực của provider đang chạy. Không tự sinh mock result, không
hứa hỗ trợ X-Mock-Scenario header chưa được backend triển khai.

History/filter/detail/confirm dùng `/api/v1/alpr/detections`.
Real provider cần weights theo manifest/checksum và PaddleOCR model/cache;
readiness và video/benchmark thật là hai gate độc lập.
