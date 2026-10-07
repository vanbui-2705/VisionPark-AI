import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getNotifications, markAllRead, markNotificationRead, subscribeNotifications } from '../../lib/notifications.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'

export function NotificationsPage() {
  const [rows, setRows] = useState(getNotifications())
  useEffect(() => subscribeNotifications(() => setRows([...getNotifications()])), [])
  if (rows.length === 0) {
    return (
      <div style={{ display: 'grid', gap: 16 }}>
        <Breadcrumb items={[{ label: translate("Thông báo") }]} />
        <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Inbox · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>{translate("Thông báo")}</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{translate("Thông báo từ sự kiện thật, lưu theo tài khoản trong database.")}</p>
        </div>
        <EmptyState title={translate("Chưa có thông báo")} description={translate("Thông báo xuất hiện khi có sự kiện bảo mật hoặc lỗi được ghi nhận.")} />
      </div>
    )
  }
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: translate("Thông báo") }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Inbox · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>{translate("Thông báo")}</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{translate("Trạng thái đã đọc được lưu trong database.")}</p>
        </div>
        <Badge>{rows.filter((n) => !n.read).length}{translate("mới")}</Badge>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}><button type="button" className="btn btn-sm" onClick={() => void markAllRead().catch(() => undefined)}>{translate("Đánh dấu tất cả đã đọc")}</button></div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 10 }}>
        {rows.map((n) => (
          <li key={n.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 14, display: 'flex', gap: 12, alignItems: 'center', opacity: n.read ? 0.7 : 1, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
            <Badge variant={n.read ? 'neutral' : 'info'}>{n.read ? translate("Đã đọc") : translate("Mới")}</Badge>
            <div style={{ flex: 1 }}>
              <b style={{ fontSize: 13 }}>{translate(n.title)}</b> <span className="muted" style={{ fontSize: 13 }}>{n.message}</span>
              <div className="muted" style={{ fontSize: 12 }}>{new Date(n.time).toLocaleString('vi-VN')}</div>
            </div>
            {n.to ? <Link to={n.to} onClick={() => void markNotificationRead(n.id).catch(() => undefined)} className="btn btn-sm">{translate("Mở")}</Link> : null}
            {!n.read ? <button type="button" className="btn btn-ghost btn-sm" onClick={() => void markNotificationRead(n.id).catch(() => undefined)}>{translate("Đã đọc")}</button> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
