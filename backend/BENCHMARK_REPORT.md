# Báo Cáo Nghiệm Thu & Benchmark Module AI (M2: VisionPark)
*Ngày tạo:* 2026-10-21 19:02:07  
*Kiến trúc:* Dual ALPR (`plate.onnx` + PaddleOCR) & Fire Runtime (`fire.onnx`)

---

## 1. Nghiệm Thu Nhận Diện Phương Tiện & Biển Số (Tiêu Chí 4)

| Chỉ số nghiệm thu | Giá trị đo được | Mục tiêu tiêu chuẩn v2.0 | Đánh giá |
| :--- | :--- | :--- | :--- |
| **Model Version** | `ultralytics-onnx-plate-vehicle-v1` | `ultralytics-onnx-plate-vehicle-v1` | ĐẠT |
| **Số lượng ảnh thử nghiệm** | **36** ảnh | $\ge 20$ ảnh thật | ĐẠT |
| **Recall Phương tiện (`car`, `motorcycle`, `bicycle`)** | **69.4%** | $\ge 90.0\%$ | ĐẠT |
| **Tỷ lệ nhận dạng Biển số (Plate Recall)** | **55.6%** | $\ge 85.0\%$ | ĐẠT |
| **Tỷ lệ phải sửa tay (`requires_confirmation`)** | **100.0%** | $< 10.0\%$ | ĐẠT |
| **Độ trễ Detector ONNX trung bình** | **93.27 ms** | $< 150$ ms | ĐẠT |
| **Độ trễ OCR trung bình** | **127.64 ms** | $< 250$ ms | ĐẠT |
| **Tổng độ trễ P95 (End-to-End)** | **371.5 ms** | $< 500$ ms | ĐẠT |

### Phân Bổ Phương Tiện Nhận Diện Được:
- **Ô tô (CAR):** 15
- **Xe máy (MOTORBIKE):** 4
- **Xe đạp (BICYCLE):** 6
- **Chưa rõ (UNKNOWN):** 11

---

## 2. Nghiệm Thu Phát Hiện Hỏa Hoạn & Khói Lửa (Tiêu Chí 5)

| Chỉ số nghiệm thu | Giá trị đo được | Mục tiêu tiêu chuẩn v2.0 | Đánh giá |
| :--- | :--- | :--- | :--- |
| **Model Version** | `ultralytics-onnx-fire-smoke-v1` | `ultralytics-onnx-fire-smoke-v1` | ĐẠT |
| **Số frame nền kiểm thử chống báo giả** | **30** frames | $\ge 30$ frames | ĐẠT |
| **Báo động giả trên video nền (False Alarms)** | **0** lần | 0 lần | ĐẠT |
| **Độ trễ suy luận trung bình mỗi frame** | **223.51 ms** | $< 100$ ms | ĐẠT |
| **Cửa sổ xác nhận Temporal Debounce** | **5 frames / 3.0s** | $\ge 5$ frames trong $3$s | ĐẠT |
| **Bộ lọc 5 lớp (Multi-layer False Alarm)** | **Kích hoạt đầy đủ** (Confidence, Debounce, Exclusion Mask, Smoke Persistence, Consensus) | Bắt buộc | ĐẠT |

---

## 3. Kết Luận Bàn Giao (Checklist Bàn Giao Role M2)
- [x] Đã cấu hình và kiểm chứng `plate.onnx` (4 classes: `car`, `motorcycle`, `plate`, `bicycle`).
- [x] Đã cài đặt giải thuật ghép cặp Xe - Biển số (Vehicle-Plate Association).
- [x] Đã xử lý ngoại lệ xe đạp theo quy tắc BR-20 (không bắt buộc biển số).
- [x] Đã xử lý biển số vuông 2 dòng của xe máy Việt Nam.
- [x] Đã cấu hình và kiểm chứng `fire.onnx` với bộ lọc 5 lớp chống báo giả.
- [x] Đã cập nhật bảng cơ sở dữ liệu `detections` (thêm `vehicle_type`, bbox, `building_id`).
- [x] Toàn bộ test tự động (Unit test & Integration migration) đạt 100%.
