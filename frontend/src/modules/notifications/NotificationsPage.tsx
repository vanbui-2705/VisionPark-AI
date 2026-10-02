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
        <Breadcrumb items={[{ label: 'Thông báo' }]} />
        <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Inbox · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Thông báo</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Thông báo nội bộ frontend — chỉ xuất hiện khi có hành động thực.</p>
        </div>
        <EmptyState title="Chưa có thông báo" description="Thông báo nội bộ frontend — chỉ xuất hiện khi có hành động thực (xác nhận biển số, lưu dữ liệu, lỗi). Không fake notification server." />
      </div>
    )
  }
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Thông báo' }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Inbox · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Thông báo</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Thông báo nội bộ frontend — không fake server.</p>
        </div>
        <Badge>{rows.filter((n) => !n.read).length} mới</Badge>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}><button type="button" className="btn btn-sm" onClick={() => markAllRead()}>Đánh dấu tất cả đã đọc</button></div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 10 }}>
        {rows.map((n) => (
          <li key={n.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 14, display: 'flex', gap: 12, alignItems: 'center', opacity: n.read ? 0.7 : 1, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
            <Badge variant={n.read ? 'neutral' : 'info'}>{n.read ? 'Đã đọc' : 'Mới'}</Badge>
            <div style={{ flex: 1 }}>
              <b style={{ fontSize: 13 }}>{n.title}</b> <span className="muted" style={{ fontSize: 13 }}>{n.message}</span>
              <div className="muted" style={{ fontSize: 12 }}>{new Date(n.time).toLocaleString('vi-VN')}</div>
            </div>
            {n.to ? <Link to={n.to} onClick={() => markNotificationRead(n.id)} className="btn btn-sm">Mở</Link> : null}
            {!n.read ? <button type="button" className="btn btn-ghost btn-sm" onClick={() => markNotificationRead(n.id)}>Đã đọc</button> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
