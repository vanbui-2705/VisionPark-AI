import { t as translate } from "../../lib/i18n"
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
export function HelpPage() {
  return (
    <div className="utility-page">
      <Breadcrumb items={[{ label: translate("Trợ giúp") }]} />
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Guide · Duy Anh</span>
          <h1>{translate("Trợ giúp")}</h1>
          <p>{translate("Vai trò, trạm quét, ALPR Test Lab và cách gửi mã hỗ trợ khi gặp lỗi.")}</p>
        </div>
      </section>
      {[
        { title: translate("Vai trò"), body: <ul style={{ margin: 0, paddingLeft: 18 }}><li><b>ADMIN:</b> {translate("Dashboard, Làn xe (CRUD không xóa), Người dùng, Vai trò/Phân quyền, ALPR Test Lab, Audit Logs, Error Center, System Health.")}</li><li><b>OPERATOR:</b> {translate("Quét biển số, Lịch sử nhận diện, Xem làn xe, Xác nhận/sửa biển số, Hồ sơ/Cài đặt/Thông báo/Trợ giúp.")}</li><li>{translate("Sidebar dùng")} <code>can(user, permission)</code> {translate("— backend là authority.")}</li></ul> },
        { title: translate("Trạm quét"), body: <p style={{ margin: 0 }}>{translate("Chọn làn vào và chế độ Ảnh JPEG/PNG hoặc Video MP4. Nhận diện bằng YOLO/OCR thật, kiểm tra biển số rồi xác nhận hoặc sửa. Nhập thủ công khi không đọc được. Kết quả cuối và giao dịch được lưu; preview không lưu mỗi frame.")}</p> },
        { title: 'ALPR Test Lab', body: <p style={{ margin: 0 }}>{translate("Chọn ảnh và làn, bấm Chạy nhận diện để xem kết quả. Bấm Lưu kết quả để lưu detection và ảnh vào lịch sử; thao tác này không tạo giao dịch xe vào.")}</p> },
        { title: translate("Sự cố"), body: <p style={{ margin: 0 }}>{translate("Gặp lỗi API → mở Error Center; copy")} <b>{translate("Mã hỗ trợ")}</b> {translate("(correlationId) gửi quản trị viên.")} <Badge>Tip</Badge></p> },
      ].map((s) => (
        <section key={s.title} className="utility-panel help-panel">
          <h3>{translate(s.title)}</h3>
          <div className="help-panel-body">{s.body}</div>
        </section>
      ))}
    </div>
  )
}
