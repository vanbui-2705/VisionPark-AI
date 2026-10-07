import { t as translate } from "../../lib/i18n"
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
export function HelpPage() {
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: translate("Trợ giúp") }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Guide · Duy Anh</div>
        <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>{translate("Trợ giúp")}</h2>
        <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{translate("Vai trò, trạm quét, ALPR Test Lab và cách gửi mã hỗ trợ khi gặp lỗi.")}</p>
      </div>
      {[
        { title: translate("Vai trò"), body: <ul style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 6 }}><li><b>ADMIN:</b>{translate("Dashboard, Làn xe (CRUD không xóa), Người dùng, Vai trò/Phân quyền, ALPR Test Lab, Audit Logs, Error Center, System Health.")}</li><li><b>OPERATOR:</b>{translate("Quét biển số, Lịch sử nhận diện, Xem làn xe, Xác nhận/sửa biển số, Hồ sơ/Cài đặt/Thông báo/Trợ giúp.")}</li><li>{translate("Sidebar dùng")}<code>can(user, permission)</code>{translate("— backend là authority.")}</li></ul> },
        { title: translate("Trạm quét"), body: <p>{translate("Chọn làn vào và chế độ Ảnh JPEG/PNG hoặc Video MP4. Nhận diện bằng YOLO/OCR thật, kiểm tra biển số rồi xác nhận hoặc sửa. Nhập thủ công khi không đọc được. Kết quả cuối và giao dịch được lưu; preview không lưu mỗi frame.")}</p> },
        { title: 'ALPR Test Lab', body: <p>{translate("Chọn ảnh và làn, bấm Chạy nhận diện để xem kết quả. Bấm Lưu kết quả để lưu detection và ảnh vào lịch sử; thao tác này không tạo giao dịch xe vào.")}</p> },
        { title: translate("Sự cố"), body: <p style={{ margin: 0 }}>{translate("Gặp lỗi API → mở Error Center; copy")}<b>{translate("Mã hỗ trợ")}</b>{translate("(correlationId) gửi quản trị viên.")}<Badge>Tip</Badge></p> },
      ].map((s) => (
        <section key={s.title} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <h3 style={{ margin: '0 0 10px' }}>{translate(s.title)}</h3>
          <div style={{ fontSize: 13, color: 'var(--text)' }}>{s.body}</div>
        </section>
      ))}
    </div>
  )
}
