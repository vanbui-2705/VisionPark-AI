import { useAuth } from '../auth/AuthContext.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { useNavigate } from 'react-router-dom'

export function ProfilePage() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const initial = user ? (user.display_name?.[0] ?? user.username[0]).toUpperCase() : '?'
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.16)', display: 'grid', placeItems: 'center', fontSize: 24, fontWeight: 800 }}>{initial}</div>
          <div>
            <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Account · Duy Anh</div>
            <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Hồ sơ cá nhân</h2>
            <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{user?.display_name ?? user?.username ?? '—'}</p>
          </div>
        </div>
        <Badge variant={user?.active ? 'success' : 'danger'}>{user?.active ? 'Active' : 'Inactive'}</Badge>
      </div>

      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)' }}>Display Name</span><strong>{user?.display_name ?? '—'}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)' }}>Username</span><code>{user?.username ?? '—'}</code></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)' }}>Role</span><Badge>{user?.role ?? '—'}</Badge></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)' }}>Status</span><span>{user?.active ? 'Active' : 'Inactive'}</span></div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          <Button variant="secondary" disabled title="Chờ Backend API">Đổi mật khẩu — Chờ Backend</Button>
          <Button variant="secondary" onClick={() => { logout(); nav('/login') }}>Đăng xuất</Button>
        </div>
      </section>
    </div>
  )
}
