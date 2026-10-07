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
      <div className="utility-page notifications-page">
        <Breadcrumb items={[{ label: 'Thông báo' }]} />
        <section className="utility-hero utility-hero--forest">
          <div className="utility-hero-copy">
            <span className="utility-kicker">Hộp thư thông báo · VisionPark</span>
            <h1>Thông báo</h1>
            <p>Sự kiện xác nhận biển số, lưu trữ và thao tác vận hành.</p>
          </div>
        </section>
        <section className="utility-panel notifications-empty"><EmptyState title="Chưa có thông báo" description="Chưa có thông báo mới nào phát sinh từ các thao tác gần đây." /></section>
      </div>
    )
  }
  return (
    <div className="utility-page notifications-page">
      <Breadcrumb items={[{ label: 'Thông báo' }]} />
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Hộp thư thông báo · VisionPark</span>
          <h1>Thông báo</h1>
          <p>Sự kiện xác nhận biển số, lưu trữ và thao tác vận hành.</p>
        </div>
        <div className="utility-hero-stat"><strong>{rows.filter((n) => !n.read).length}</strong><span>chưa đọc</span></div>
      </section>
      <div className="notifications-toolbar"><button type="button" className="btn btn-sm" onClick={() => markAllRead()}>Đánh dấu tất cả đã đọc</button></div>
      <ul className="notification-list">
        {rows.map((n) => (
          <li key={n.id} className={`notification-item${n.read ? ' is-read' : ''}`}>
            <Badge variant={n.read ? 'neutral' : 'info'}>{n.read ? 'Đã đọc' : 'Mới'}</Badge>
            <div className="notification-copy">
              <div><b>{n.title}</b> <span className="muted">{n.message}</span></div>
              <time className="muted" dateTime={n.time}>{new Date(n.time).toLocaleString('vi-VN')}</time>
            </div>
            {n.to ? <Link to={n.to} onClick={() => markNotificationRead(n.id)} className="btn btn-sm">Mở</Link> : null}
            {!n.read ? <button type="button" className="btn btn-ghost btn-sm" onClick={() => markNotificationRead(n.id)}>Đã đọc</button> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
