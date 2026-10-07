import { t as translate } from "../../lib/i18n"
import { Link, useLocation } from 'react-router-dom'

// Mã hỗ trợ suy ra từ đường dẫn (pure — không Math.random trong render).
function supportCode(pathname: string) {
  let h = 0
  for (const ch of pathname) h = ((h << 5) - h + ch.charCodeAt(0)) | 0
  return 'c8f4-' + (h >>> 0).toString(16).padStart(8, '0')
}

export function ForbiddenPage() {
  const { pathname } = useLocation()
  return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <h1>{translate("403 — Không có quyền truy cập")}</h1>
      <p className="muted">{translate("Bạn không có quyền xem trang này. Vui lòng liên hệ quản trị viên.")}</p>
      <p>{translate("Mã hỗ trợ:")}{supportCode(pathname)}</p>
      <Link to="/" className="btn btn-primary">{translate("Về trang chủ")}</Link>
    </div>
  )
}
export function NotFoundPage() {
  const { pathname } = useLocation()
  return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <h1>{translate("404 — Không tìm thấy trang")}</h1>
      <p className="muted">{translate("Đường dẫn không tồn tại.")}</p>
      <p>{translate("Mã hỗ trợ:")}{supportCode(pathname)}</p>
      <Link to="/" className="btn btn-primary">{translate("Về trang chủ")}</Link>
    </div>
  )
}
