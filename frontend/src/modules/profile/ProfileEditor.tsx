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
  return (
    <div className="data-page">
      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">ACCOUNT · VISIONPARK</span>
          <h2>{translate("Hồ sơ cá nhân")}</h2>
          <p>{user?.username} · {user?.role}</p>
        </div>
        <div className="data-hero-stat">
          <strong>{user?.role ?? '—'}</strong>
          <span>{user?.username ?? '—'}</span>
        </div>
      </section>

      {error && <Alert variant="error">{error}</Alert>}
      {message && <Alert variant="success">{message}</Alert>}

      <div className="grid-2" style={{ alignItems: 'start' }}>
        <section className="card card-polished">
          <div className="card-head">
            <div>
              <span className="card-kicker">IDENTITY</span>
              <h3>{translate("Hồ sơ cá nhân")}</h3>
            </div>
          </div>
          <form className="stack" onSubmit={e => { e.preventDefault(); void save() }}>
            <label className="field"><span>{translate("Tên hiển thị")}</span><input value={name} required maxLength={120} disabled={busy} onChange={e => setName(e.target.value)} /></label>
            <label className="field"><span>Email</span><input type="email" value={email} disabled={busy} onChange={e => setEmail(e.target.value)} /></label>
            <div className="row-actions" style={{ marginTop: 4 }}>
              <button className="btn btn-primary" disabled={busy}>{translate("Lưu hồ sơ")}</button>
              <button type="button" className="btn" disabled={busy} onClick={logout}>{translate("Đăng xuất")}</button>
            </div>
          </form>
        </section>

        <section className="card card-polished">
          <div className="card-head">
            <div>
              <span className="card-kicker">SECURITY</span>
              <h3>{translate("Đổi mật khẩu")}</h3>
            </div>
          </div>
          <form className="stack" onSubmit={e => { e.preventDefault(); void save(true) }}>
            <label className="field"><span>{translate("Mật khẩu hiện tại")}</span><input type="password" autoComplete="current-password" required value={current} disabled={busy} onChange={e => setCurrent(e.target.value)} /></label>
            <label className="field"><span>{translate("Mật khẩu mới")}</span><input type="password" autoComplete="new-password" minLength={8} required value={password} disabled={busy} onChange={e => setPassword(e.target.value)} /></label>
            <p className="muted" style={{ fontSize: 12, margin: 0 }}>{translate("Đổi mật khẩu sẽ thu hồi các phiên và yêu cầu đăng nhập lại.")}</p>
            <div className="row-actions" style={{ marginTop: 4 }}>
              <button className="btn btn-primary" disabled={busy}>{translate("Đổi mật khẩu")}</button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}
