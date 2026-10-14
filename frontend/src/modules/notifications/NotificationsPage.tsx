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
      <div className="utility-page">
        <Breadcrumb items={[{ label: translate("Thông báo") }]} />
        <section className="utility-hero utility-hero--forest">
          <div className="utility-hero-copy">
            <span className="utility-kicker">Inbox · Duy Anh</span>
            <h1>{translate("Thông báo")}</h1>
            <p>{translate("Thông báo từ sự kiện thật, lưu theo tài khoản trong database.")}</p>
          </div>
        </section>
        <EmptyState title={translate("Chưa có thông báo")} description={translate("Thông báo xuất hiện khi có sự kiện bảo mật hoặc lỗi được ghi nhận.")} />
      </div>
    )
  }
  return (
    <div className="utility-page">
      <Breadcrumb items={[{ label: translate("Thông báo") }]} />
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Inbox · Duy Anh</span>
          <h1>{translate("Thông báo")}</h1>
          <p>{translate("Trạng thái đã đọc được lưu trong database.")}</p>
        </div>
        <div className="utility-hero-stat">
          <strong>{rows.filter((n) => !n.read).length}</strong>
          <span>{translate("mới")}</span>
        </div>
      </section>
      <div className="notifications-toolbar">
        <button type="button" className="btn btn-sm" onClick={() => void markAllRead().catch(() => undefined)}>{translate("Đánh dấu tất cả đã đọc")}</button>
      </div>
      <ul className="notification-list">
        {rows.map((n) => (
          <li key={n.id} className={`notification-item ${n.read ? 'is-read' : ''}`}>
            <Badge variant={n.read ? 'neutral' : 'info'}>{n.read ? translate("Đã đọc") : translate("Mới")}</Badge>
            <div className="notification-copy">
              <b>{translate(n.title)}</b> <span>{n.message}</span>
              <time className="muted">{new Date(n.time).toLocaleString('vi-VN')}</time>
            </div>
            {n.to ? <Link to={n.to} onClick={() => void markNotificationRead(n.id).catch(() => undefined)} className="btn btn-sm">{translate("Mở")}</Link> : null}
            {!n.read ? <button type="button" className="btn btn-ghost btn-sm" onClick={() => void markNotificationRead(n.id).catch(() => undefined)}>{translate("Đã đọc")}</button> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
