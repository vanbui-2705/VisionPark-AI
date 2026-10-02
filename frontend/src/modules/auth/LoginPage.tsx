import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../../api/errors.ts'
import { useAuth } from './AuthContext.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'

export function LoginPage() {
  const { login, loading, isAuthenticated, user } = useAuth()
  const [search] = useSearchParams()
  const nav = useNavigate()
  const [username, setUsername] = useState(() => localStorage.getItem('visionpark.remember_user') ?? '')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [remember, setRemember] = useState(() => !!localStorage.getItem('visionpark.remember_user'))
  const [err, setErr] = useState<string | null>(null)
  const [touched, setTouched] = useState(false)

  const expired = search.get('reason') === 'expired'
  const returnUrl = search.get('returnUrl')

  const targetAfterLogin = useMemo(() => {
    if (returnUrl && returnUrl.startsWith('/') && !returnUrl.startsWith('//')) return returnUrl
    return user?.role === 'ADMIN' ? '/admin/dashboard' : '/station/scan'
  }, [returnUrl, user?.role])

  useEffect(() => {
    if (isAuthenticated) nav(targetAfterLogin, { replace: true })
  }, [isAuthenticated, targetAfterLogin, nav])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!username.trim() || !password) return
    setErr(null)
    try {
      await login(username.trim(), password)
      if (remember) localStorage.setItem('visionpark.remember_user', username.trim())
      else localStorage.removeItem('visionpark.remember_user')
    } catch (e2: unknown) {
      if (e2 instanceof ApiError) {
        if (e2.status === 401) setErr('Tên đăng nhập hoặc mật khẩu không đúng.')
        else if (e2.code === 'NETWORK_ERROR' || e2.code === 'TIMEOUT') setErr('Không thể kết nối tới máy chủ. Vui lòng thử lại.')
        else setErr(e2.message || 'Đăng nhập thất bại.')
      } else if (e2 instanceof Error) setErr(e2.message)
      else setErr('Đăng nhập thất bại.')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--wide auth-card--login">
        <section className="auth-showcase" aria-label="VisionPark Smart Parking Management">
          <div className="auth-logo">
            <span className="auth-logo-mark" aria-hidden="true">V</span>
            <span className="auth-logo-word">Vision<span>Park</span></span>
          </div>
          <div className="auth-showcase-copy">
            <p className="auth-showcase-kicker"><span aria-hidden="true" /> QUẢN LÝ BÃI XE THÔNG MINH</p>
            <h1>Vận hành bãi xe.<br /><span>Nhẹ nhàng hơn.</span></h1>
            <p>Mọi thông tin vận hành trong tầm tay — để bạn tập trung vào điều quan trọng nhất.</p>
          </div>
          <div className="auth-showcase-footer">
            <span>VISIONPARK</span>
            <span>SMART PARKING MANAGEMENT</span>
          </div>
        </section>

        <section className="auth-panel" aria-labelledby="login-heading">
          <header className="auth-panel-heading">
            <p className="auth-panel-kicker">CỔNG ĐIỀU HÀNH</p>
            <h2 id="login-heading">Chào mừng <span>trở lại</span></h2>
            <p>Đăng nhập để tiếp tục công việc của bạn.</p>
          </header>
          {expired ? <Alert variant="warning">Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.</Alert> : null}
          {err ? <Alert variant="error">{err}</Alert> : null}
          <form onSubmit={onSubmit} noValidate>
            <Input
              label="Tên đăng nhập"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={touched && !username.trim() ? 'Tên đăng nhập không được để trống' : undefined}
            />
            <div className="field">
              <label htmlFor="password">Mật khẩu</label>
              <div className={`input-with-action password-control${show ? ' is-visible' : ''}`}>
                <input
                  id="password"
                  name="password"
                  type={show ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={touched && !password ? true : undefined}
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShow((v) => !v)}
                  aria-pressed={show}
                  aria-label={show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  title={show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                >
                  <span className="password-toggle-icon" aria-hidden="true">
                    <svg className="eye-icon eye-icon--open" viewBox="0 0 24 24" fill="none">
                      <path d="M2.5 12s3.4-5 9.5-5 9.5 5 9.5 5-3.4 5-9.5 5-9.5-5-9.5-5Z" />
                      <circle cx="12" cy="12" r="2.5" />
                    </svg>
                    <svg className="eye-icon eye-icon--closed" viewBox="0 0 24 24" fill="none">
                      <path d="m3 3 18 18M10.6 6.2A10.7 10.7 0 0 1 12 6c6.1 0 9.5 6 9.5 6a17 17 0 0 1-3.1 3.4M6.2 6.8C3.8 8.3 2.5 12 2.5 12s3.4 6 9.5 6c1 0 1.9-.2 2.7-.5" />
                      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
                    </svg>
                  </span>
                  <span className="password-toggle-label">{show ? 'Ẩn' : 'Hiện'}</span>
                </button>
              </div>
              {touched && !password ? <span className="field-error">Mật khẩu không được để trống</span> : null}
            </div>
            <label className="checkbox">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Ghi nhớ đăng nhập
            </label>
            <Button type="submit" loading={loading} style={{ width: '100%', marginTop: 12 }}>
              Đăng nhập
            </Button>
          </form>
          <p className="auth-foot">
            Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
          </p>
          <p className="auth-hint">Tài khoản demo: admin / admin (ADMIN) · operator / admin (OPERATOR)</p>
        </section>
      </div>
    </div>
  )
}
