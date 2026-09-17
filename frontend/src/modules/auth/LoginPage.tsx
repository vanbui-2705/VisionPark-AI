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
      <div className="auth-card auth-card--wide">
        <div className="auth-brand">
          <div className="auth-logo">◉ VisionPark</div>
          <p className="auth-subtitle">Smart Parking Management</p>
        </div>
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
            <div className="input-with-action">
              <input
                id="password"
                name="password"
                type={show ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={touched && !password ? true : undefined}
              />
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShow((v) => !v)} aria-label={show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}>
                {show ? 'Ẩn' : 'Hiện'}
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
      </div>
    </div>
  )
}
