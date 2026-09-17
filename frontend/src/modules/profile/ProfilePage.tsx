import { useAuth } from '../auth/AuthContext.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { useNavigate } from 'react-router-dom'

export function ProfilePage() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div>
      <h2>Hồ sơ cá nhân</h2>
      <section className="card" style={{marginTop:12}}>
        <ul className="kv">
          <li>Display Name: {user?.display_name ?? '—'}</li>
          <li>Username: {user?.username ?? '—'}</li>
          <li>Role: {user?.role ?? '—'}</li>
          <li>Status: {user?.active ? 'Active' : 'Inactive'}</li>
        </ul>
        <div style={{display:'flex', gap:8, marginTop:12}}>
          <Button variant="secondary" disabled title="Chờ Backend API">Đổi mật khẩu — Chờ Backend</Button>
          <Button variant="secondary" onClick={()=> { logout(); nav('/login')}}>Đăng xuất</Button>
        </div>
      </section>
    </div>
  )
}
