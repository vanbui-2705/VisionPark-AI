# VisionPark: đối chiếu thị trường và hướng nâng cấp

Ngày khảo sát: 05/11/2026, theo múi giờ Việt Nam. Phạm vi: nguồn công khai chính thức của nhà cung cấp tại Việt Nam và quốc tế; chưa thử sản phẩm, đo hiệu năng hay lấy báo giá. Tính năng được nhà cung cấp công bố không đồng nghĩa đã được kiểm chứng độc lập.

## 1. Điều thị trường đã có

| Nguồn sơ cấp | Nhà cung cấp công bố | Ý nghĩa đối với VisionPark — nhận định của người nghiên cứu |
| --- | --- | --- |
| [AzParking — trang sản phẩm](https://www.azparking.vn/) | Vé lượt/tháng, nhận diện biển số, camera/barrier, ca trực, đối soát vé–xe–tiền và quản lý nhiều điểm. | OCR, dashboard và vé tháng đã là nhóm chức năng phổ biến trong mẫu khảo sát, khó dùng riêng chúng để tạo lợi thế. |
| [SmartParking của Mega — gói cho thuê](https://smartparking.vn/smartparking-goi-cho-thue/) | Thanh toán QR động hoặc tiền mặt; nhiều hãng thiết bị; lưu lịch sử và ảnh khi cưỡng bức mở barrier; cảnh báo thẻ mất/danh sách đen. | Thu tiền mặt nhanh là nền vận hành hữu ích, nhưng hỗ trợ QR và xử lý ngoại lệ có chứng cứ là hướng bổ sung có cơ sở thị trường. |
| [Vinparking — phần mềm bãi giữ xe](https://vinparking.com/san-pham/phan-mem-quan-ly-bai-giu-xe-5) | Quản trị bằng web/mobile, báo cáo email kèm Excel, nhiều camera/đầu đọc thẻ và hỗ trợ chuyển dữ liệu từ phần mềm khác. | Gói chuyển đổi từ hệ thống cũ có thể giúp bán hàng tốt hơn một màn hình quản trị mới. |
| [SKIDATA — mô tả nền tảng chính thức](https://www.skidata.com/grounding-company) | Kết hợp cloud với vận hành cục bộ; quy trình truy cập và doanh thu trọng yếu có thể tiếp tục khi mất kết nối; quản lý nhiều điểm, đặt chỗ và thuê bao. | Khả năng qua cổng khi đứt Internet cần thành điều kiện nghiệm thu, không chỉ là thông báo mất mạng trên UI. |
| [Amano McGann — tích hợp bên thứ ba](https://amanomcgann.com/our-solutions-parking-management/third-party-integrations/) | API tích hợp đặt chỗ/trung tâm hỗ trợ; BI về lượng xe, doanh thu và thời gian đỗ; liên kết vé với biển số; tích hợp chỉ dẫn chỗ trống. | API và dữ liệu vận hành đáng tin giúp mở rộng hệ sinh thái sau khi luồng vào–ra và thu phí ổn định. |

Không kết luận “mọi hệ thống cũ đều thiếu AI/cloud/QR”. Ngay mẫu khảo sát này đã có các chức năng đó. Cũng không dùng quảng cáo “100% chính xác” làm mốc so sánh: trang Vinparking đồng thời có tuyên bố tuyệt đối và FAQ ghi trên 95% khi hình ảnh đạt yêu cầu. Không có cùng dữ liệu thử, camera và định nghĩa phép đo để so sánh trực tiếp với benchmark của VisionPark. [Nguồn Vinparking](https://vinparking.com/san-pham/phan-mem-quan-ly-bai-giu-xe-5).

## 2. Liên hệ với repo hiện tại

Các nhận định sau là kết quả đọc tài liệu/code, chưa phải xác nhận vận hành tại bãi:

- [README](../README.md) còn mô tả checkout, pricing, vé tháng và barrier ngoài phạm vi; trong khi repo đã có các module tương ứng. Cần dùng báo cáo kiểm tra chức năng riêng để xác nhận mức triển khai, tránh kết luận dựa vào README cũ.
- [Kế hoạch bàn giao](phan-cong-nhiem-vu-5-thanh-vien.md) phiên bản 2 ngày 02/11/2026 chủ động chọn CASH, bỏ online/VietQR/webhook trong đợt bàn giao. Do đó QR bên dưới là đề xuất cho giai đoạn sau, không phải lỗi thiếu phạm vi của đợt này.
- Tài liệu trên đặt mục tiêu ALPR exact match ít nhất 80% và p95 không quá 1.000 ms. Đây là mục tiêu nội bộ; chưa chứng minh mức phù hợp tự động mở barrier trong mọi điều kiện thực tế.
- [Backend Phase 3 API handoff](backend-core-phase-3-api.md) đã mô tả building scope, vai trò và cấu hình readiness. Multi-site nên phát triển từ nền này, không xây thêm một cơ chế tenant song song.

## 3. Thứ tự đầu tư đề xuất

Các mục sau là khuyến nghị kỹ thuật/sản phẩm của người nghiên cứu, không phải tính năng đã kiểm chứng trong VisionPark. Giá trị và độ khó là đánh giá định tính; chưa có số liệu ROI thực tế.

| Ưu tiên | Nâng cấp | Giá trị kinh doanh dự kiến | Bằng chứng cần có trước khi quảng bá |
| --- | --- | --- | --- |
| P0 | Luồng vào–ra–tính phí–thu tiền–mở cổng trọn vẹn; cơ chế thử lại không thu trùng | Có thể vận hành một bãi nhỏ và giải trình giao dịch | UAT chạy xuyên suốt; hai nhân viên thao tác đồng thời; timeout sau commit; thu phí đúng qua đêm và khi đổi giá |
| P0 | ALPR cho xe máy/biển hai dòng, ngày đêm; tự chuyển người duyệt khi không chắc | Giảm thao tác bảo vệ và sai biển | Tập đánh giá độc lập từ bãi dự kiến lắp; báo cáo exact match, tỷ lệ phải sửa, tỷ lệ nhận nhầm, p95 theo nhóm điều kiện |
| P0 | Camera/RTSP và barrier thật, trạng thái thiết bị, xác nhận lệnh và cảm biến | Thay thế được quy trình thực thay vì chỉ demo bằng ảnh | Thử thiết bị thật; kiểm tra camera mất kết nối, lệnh timeout, nhấn lại, cảm biến vật cản, dừng/mở khẩn cấp |
| P1 | Vận hành tại bãi khi đứt Internet, đồng bộ sau kết nối | Tránh ùn tắc do sự cố mạng ngoài bãi | Ngắt Internet thật; vẫn tra vé và thu tiền trên LAN; kết nối lại không tạo phiên/thu tiền trùng; quy tắc xung đột rõ ràng |
| P1 | Ca thu ngân: tiền đầu ca, số phải thu, tiền đếm, chênh lệch, ký bàn giao | Chủ bãi kiểm soát thất thoát, kế toán dễ đối soát | Báo cáo từ sổ giao dịch bất biến; hoàn/miễn/giảm có quyền và lý do; ca chốt không sửa âm thầm |
| P1 | Chống tráo xe/mượn thẻ: ảnh vào–ra, biển/thẻ/xe; ngoại lệ có duyệt | Giảm tranh chấp và mở cổng sai | Kịch bản thẻ khác xe, sửa biển, mất thẻ, mở tay; ai duyệt và vì sao phải truy được |
| P1 | Bộ tích hợp và chuyển đổi hệ thống cũ | Giảm chi phí thay mới và gián đoạn triển khai | Danh sách hãng/model/firmware thực sự đã thử; nhập vé tháng, thẻ và xe đang trong bãi có bản xem trước, đối chiếu và phương án quay lui |
| P2 | QR động theo giao dịch, callback xác thực, đối soát ngân hàng; giữ CASH dự phòng | Giảm xử lý tiền mặt, phù hợp thói quen người dùng | Sandbox và giao dịch thật nhỏ; kiểm tra callback lặp/giả/chậm/sai tiền; trạng thái thanh toán tách khỏi trạng thái barrier |
| P2 | Cổng cư dân/doanh nghiệp: đăng ký, gia hạn vé tháng, nhắc hạn, lịch sử, hạn mức chỗ | Tăng tự phục vụ và doanh thu định kỳ | Thanh toán/gia hạn đồng bộ đúng quyền ra vào; đổi biển và nhiều xe một vé có chính sách rõ |
| P2 | Dashboard nhiều bãi: doanh thu, chỗ trống, hàng chờ, thiết bị lỗi | Chủ chuỗi quản lý từ xa và xử lý sự cố sớm | Cách ly dữ liệu giữa tòa nhà; chỉ số có định nghĩa; cảnh báo dựa trên dữ liệu cập nhật và ngưỡng đã thử |
| P3 | Booking, voucher cửa hàng, dự báo giờ cao điểm, tìm chỗ trống | Tạo dịch vụ bổ sung sau khi vận hành ổn định | Có nhu cầu khách hàng thật; dữ liệu vị trí/occupancy đáng tin; xử lý đặt chỗ nhưng không đến và tránh bán vượt chỗ |

Chọn giao thức theo phần cứng thực tế: RTSP cho luồng camera, ONVIF khi thiết bị và chức năng cần dùng có hỗ trợ, SDK/HTTP/TCP/serial cho controller tùy hãng. Đây là đề xuất thiết kế adapter, không phải khẳng định các giao thức thay thế được nhau hoặc mọi thiết bị đều tương thích. Không dùng kết quả HTTP thành công để kết luận thanh chắn đã mở; phải có phản hồi phù hợp từ controller/cảm biến hoặc quy trình người vận hành xác nhận.

Với offline, nên ưu tiên server/edge tại bãi và máy trạm dùng LAN trước khi xây đồng bộ nhiều máy chủ. Mất Internet khác với mất LAN, hỏng server hay mất điện; mỗi loại cần kịch bản riêng. UPS, khôi phục backup và cơ chế hỗ trợ hiện trường là một phần của gói triển khai. Không tự động cho xe ra chỉ vì ứng dụng không liên lạc được cloud.

## 4. Lợi thế nên chọn để thử thị trường

Đề xuất định vị ban đầu: **bãi xe hỗn hợp ô tô–xe máy cho chung cư/văn phòng vừa và nhỏ; vận hành liên tục, giảm sai sót thu ngân và tận dụng thiết bị sẵn có**. Đây là giả thuyết sản phẩm cần phỏng vấn chủ bãi, không phải kết luận thị trường đã được chứng minh.

Ba gói bằng chứng bán hàng có giá trị hơn thêm nhiều màn hình:

1. Cho chủ bãi xem một ca thực có đối soát tiền, số xe và mọi lần mở tay, kèm ảnh/chủ thể thao tác.
2. Cho họ ngắt Internet rồi tiếp tục vận hành, sau đó kiểm tra đồng bộ không mất hay nhân đôi giao dịch.
3. Thử ngay trên camera/đầu đọc của họ, dùng tập ảnh độc lập và ghi thời gian/công sức chuyển dữ liệu.

Chưa ưu tiên AI báo cháy, nhận diện khuôn mặt hay mô hình định giá phức tạp làm điểm bán đầu tiên. Cần kiểm chứng nhu cầu, dữ liệu và chất lượng riêng cho từng tính năng; việc một mô hình tải thành công không chứng minh khả năng vận hành của nó.

## 5. Đo giá trị trong pilot

Chạy quan sát có người vận hành tại một bãi trước khi cam kết SLA. Ghi baseline rồi so sánh sau triển khai: thời gian phục vụ p50/p95 từng làn, tỷ lệ sửa biển, số giao dịch phải xử lý tay, chênh lệch tiền cuối ca, số lần thu trùng/mất giao dịch, phút gián đoạn và thời gian hỗ trợ.

Ước tính lợi ích mỗi tháng bằng thời gian nhân viên tiết kiệm quy đổi chi phí, cộng thất thoát giảm và doanh thu phục vụ thêm, rồi trừ phần mềm, hạ tầng, phí thanh toán, bảo trì và hỗ trợ. Không cộng trùng lợi ích của cùng một giờ lao động; không cam kết hoàn vốn khi chưa có dữ liệu pilot và báo giá thiết bị.

## 6. Giới hạn nguồn

Các trang đã được truy cập/tra cứu ngày 05/11/2026; nội dung thương mại có thể thay đổi. Trang SmartParking gói cho thuê hiển thị ngày bài viết 30/11/2023, nên cần xác nhận lại chức năng/gói hiện bán với nhà cung cấp. Tài liệu SKIDATA là mô tả do hãng tự xuất bản; cần thẩm định cấu hình cụ thể trước khi coi offline, module hay tích hợp là sẵn có trong mọi triển khai. Không suy ra thị phần, độ ổn định, giá, chất lượng OCR hoặc sản phẩm nào tốt hơn từ các trang quảng bá.
