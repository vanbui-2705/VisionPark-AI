import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/errors.ts'
import { authRegisterApi } from '../../api/services.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'

const ENABLED = import.meta.env.VITE_PUBLIC_REGISTRATION_ENABLED === 'true'
const PASS_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

function strength(p: string): { label: string; pct: number } {
  let s = 0
  if (p.length >= 8) s++
  if (/[A-Z]/.test(p)) s++
  if (/[0-9]/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  const pct = Math.min(100, s * 25 + (p.length > 12 ? 10 : 0))
  const label = s <= 1 ? 'Yếu' : s === 2 ? 'Trung bình' : s === 3 ? 'Khá' : 'Mạnh'
  return { label, pct }
}

export function RegisterPage() {
  const nav = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [touched, setTouched] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!ENABLED) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Đăng ký</h1>
          <Alert variant="info">Đăng ký tài khoản hiện không được bật. Vui lòng liên hệ quản trị viên.</Alert>
          <p>
            <Link to="/login">Quay lại đăng nhập</Link>
          </p>
        </div>
      </div>
    )
  }

  const st = strength(password)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    setErr(null)
    if (!displayName.trim() || !username.trim() || !password || !confirm) return
    if (!PASS_RE.test(password)) {
      setErr('Mật khẩu tối thiểu 8 ký tự, gồm chữ và số.')
      return
    }
    if (password !== confirm) {
      setErr('Mật khẩu xác nhận không khớp.')
      return
    }
    setLoading(true)
    try {
      await authRegisterApi.register({
        username: username.trim(),
        display_name: displayName.trim(),
        email: email.trim() || undefined,
        password,
      })
      nav('/login')
    } catch (e2: unknown) {
      if (e2 instanceof ApiError) {
        if (e2.status === 409) {
          const msg = String(e2.details ?? e2.message).toLowerCase()
          if (msg.includes('username')) setErr('Tên đăng nhập đã tồn tại.')
          else if (msg.includes('email')) setErr('Email đã tồn tại.')
          else setErr('Tên đăng nhập hoặc email đã tồn tại.')
        } else setErr(e2.message)
      } else setErr(e2 instanceof Error ? e2.message : 'Đăng ký thất bại.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--wide">
        <div className="auth-brand">
          <div className="auth-logo">◉ VisionPark</div>
          <p className="auth-subtitle">Tạo tài khoản nhân viên</p>
        </div>
        {err ? <Alert variant="error">{err}</Alert> : null}
        <form onSubmit={onSubmit} noValidate>
          <Input label="Họ tên *" name="display_name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} error={touched && !displayName.trim() ? 'Họ tên không được để trống' : undefined} />
          <Input label="Tên đăng nhập *" name="username" value={username} onChange={(e) => setUsername(e.target.value)} error={touched && !username.trim() ? 'Tên đăng nhập không được để trống' : undefined} />
          <Input label="Email" name="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <div className="field">
            <label htmlFor="reg-password">Mật khẩu *</label>
            <div className="input-with-action">
              <input id="reg-password" name="password" type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={touched && !password ? true : undefined} />
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShow((v) => !v)}>
                {show ? 'Ẩn' : 'Hiện'}
              </button>
            </div>
            {password ? (
              <div className="pw-meter">
                <div className="pw-bar" style={{ width: `${st.pct}%` }} />
                <small>{st.label}</small>
              </div>
            ) : null}
            {touched && !password ? <span className="field-error">Mật khẩu không được để trống</span> : null}
          </div>
          <Input label="Xác nhận mật khẩu *" name="confirm" type={show ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} error={touched && password !== confirm ? 'Mật khẩu xác nhận không khớp' : undefined} />
          <Button type="submit" loading={loading} style={{ width: '100%', marginTop: 8 }}>
            Đăng ký
          </Button>
        </form>
        <p className="auth-foot">
          Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
        </p>
      </div>
    </div>
  )
}
