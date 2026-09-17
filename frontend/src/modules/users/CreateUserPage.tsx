import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/errors.ts'
import { usersApi } from '../../api/services.ts'
import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { useUnsavedGuard } from '../../hooks/useUnsavedGuard.ts'

export function CreateUserPage() {
  const nav = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [role, setRole] = useState<'ADMIN' | 'OPERATOR'>('OPERATOR')
  const [active, setActive] = useState(true)
  const [show, setShow] = useState(false)
  const [touched, setTouched] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const dirty = !!displayName.trim() || !!username.trim() || !!email.trim() || !!password || !!confirm
  useUnsavedGuard(dirty)

  const perms = PERMISSION_MATRIX.map((p) => ({ ...p, granted: p.perm === 'profile.read' || p.perm === 'system.read' ? true : role === 'ADMIN' ? p.admin : p.operator }))

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!displayName.trim() || !username.trim() || !password) { setErr('Vui lòng điền các trường bắt buộc.'); return }
    if (password !== confirm) { setErr('Mật khẩu xác nhận không khớp.'); return }
    if (password.length < 8) { setErr('Mật khẩu tối thiểu 8 ký tự.'); return }
    setLoading(true)
    setErr(null)
    try {
      await usersApi.create({ username: username.trim(), display_name: displayName.trim(), email: email.trim() || null, password, role, active })
      nav('/admin/users')
    } catch (e2: unknown) {
      if (e2 instanceof ApiError && e2.status === 409) setErr('Tên đăng nhập hoặc email đã tồn tại.')
      else setErr(e2 instanceof Error ? e2.message : 'Tạo tài khoản thất bại. (P1-FE-USER-API pending)')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <h2>Tạo tài khoản nhân viên</h2>
      {err ? <Alert variant="error">{err}</Alert> : null}
      <form onSubmit={onSubmit} noValidate className="form-grid">
        <section className="card">
          <h3>Thông tin cá nhân</h3>
          <Input label="Họ và tên *" value={displayName} onChange={(e) => setDisplayName(e.target.value)} error={touched && !displayName.trim() ? 'Không được để trống' : undefined} />
          <Input label="Tên đăng nhập *" value={username} onChange={(e) => setUsername(e.target.value)} error={touched && !username.trim() ? 'Không được để trống' : undefined} />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </section>
        <section className="card">
          <h3>Bảo mật</h3>
          <div className="field">
            <label>Mật khẩu *</label>
            <div className="input-with-action">
              <input type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShow((v) => !v)}>{show ? 'Ẩn' : 'Hiện'}</button>
            </div>
          </div>
          <Input label="Xác nhận mật khẩu *" type={show ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} error={touched && password !== confirm ? 'Không khớp' : undefined} />
        </section>
        <section className="card">
          <h3>Vai trò</h3>
          <Select label="Vai trò *" value={role} onChange={(e) => setRole(e.target.value as never)}>
            <option value="OPERATOR">OPERATOR</option>
            <option value="ADMIN">ADMIN</option>
          </Select>
          <div className="perm-list">
            {perms.map((p) => <div key={p.perm} className="perm-row"><span>{p.label}</span><span>{p.granted ? '✓' : '✗'}</span></div>)}
          </div>
          <label className="checkbox"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Kích hoạt tài khoản</label>
        </section>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Link to="/admin/users" className="btn">Hủy</Link>
          <Button type="submit" loading={loading}>Tạo tài khoản</Button>
        </div>
      </form>
    </div>
  )
}
