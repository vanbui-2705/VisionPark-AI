import { t as translate } from "../../lib/i18n"
import { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { apiClient } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
export function ProfileEditor() {
  const { user, refreshCurrentUser, logout } = useAuth()
  const [name, setName] = useState(user?.display_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async (changePassword = false) => {
    setBusy(true); setError(''); setMessage('')
    try {
      if (changePassword) {
        await apiClient.post('/api/v1/auth/change-password', { current_password: current, new_password: password })
        setCurrent(''); setPassword(''); logout()
      } else {
        await apiClient.patch('/api/v1/auth/me', { display_name: name, email: email || null })
        await refreshCurrentUser(); setMessage(translate("Đã lưu hồ sơ."))
      }
    } catch (e) { setError(e instanceof Error ? e.message : translate("Thao tác thất bại.")) }
    finally { setBusy(false) }
  }
  return <section className="card"><h2>{translate("Hồ sơ cá nhân")}</h2><p>{user?.username} · {user?.role}</p>
    {error && <Alert variant="error">{error}</Alert>}{message && <Alert variant="success">{message}</Alert>}
    <form onSubmit={e => { e.preventDefault(); void save() }}>
      <label>{translate("Tên hiển thị")}<input value={name} required maxLength={120} disabled={busy} onChange={e => setName(e.target.value)} /></label>
      <label>Email <input type="email" value={email} disabled={busy} onChange={e => setEmail(e.target.value)} /></label>
      <button className="btn" disabled={busy}>{translate("Lưu hồ sơ")}</button>
    </form>
    <form onSubmit={e => { e.preventDefault(); void save(true) }}><h3>{translate("Đổi mật khẩu")}</h3>
      <label>{translate("Mật khẩu hiện tại")}<input type="password" autoComplete="current-password" required value={current} disabled={busy} onChange={e => setCurrent(e.target.value)} /></label>
      <label>{translate("Mật khẩu mới")}<input type="password" autoComplete="new-password" minLength={8} required value={password} disabled={busy} onChange={e => setPassword(e.target.value)} /></label>
      <p>{translate("Đổi mật khẩu sẽ thu hồi các phiên và yêu cầu đăng nhập lại.")}</p><button className="btn" disabled={busy}>{translate("Đổi mật khẩu")}</button>
    </form>
    <button className="btn" disabled={busy} onClick={logout}>{translate("Đăng xuất")}</button>
  </section>
}
