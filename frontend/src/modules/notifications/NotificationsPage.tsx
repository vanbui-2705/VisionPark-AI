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
      <div>
        <Breadcrumb items={[{ label: 'Thông báo' }]} />
        <EmptyState title="Chưa có thông báo" description="Thông báo nội bộ frontend — chỉ xuất hiện khi có hành động thực (xác nhận biển số, lưu dữ liệu, lỗi). Không fake notification server." />
      </div>
    )
  }
  return (
    <div>
      <Breadcrumb items={[{ label: 'Thông báo' }]} />
      <div className="page-head"><h2>Thông báo</h2><p className="muted">Thông báo nội bộ frontend — không fake server.</p></div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}><button type="button" className="btn btn-sm" onClick={() => markAllRead()}>Đánh dấu tất cả đã đọc</button></div>
      <ul className="list">
        {rows.map((n) => (
          <li key={n.id} className="card" style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8, opacity: n.read ? 0.7 : 1 }}>
            <Badge variant={n.read ? 'neutral' : 'info'}>{n.read ? 'Đã đọc' : 'Mới'}</Badge>
            <div style={{ flex: 1 }}>
              <b>{n.title}</b> <span className="muted">{n.message}</span>
              <div className="muted" style={{ fontSize: 12 }}>{new Date(n.time).toLocaleString('vi-VN')}</div>
            </div>
            {n.to ? <Link to={n.to} onClick={() => markNotificationRead(n.id)}>Mở</Link> : null}
            {!n.read ? <button type="button" className="btn btn-ghost btn-sm" onClick={() => markNotificationRead(n.id)}>Đã đọc</button> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
