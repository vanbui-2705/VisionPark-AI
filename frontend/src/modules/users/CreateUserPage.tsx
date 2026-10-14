import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/errors.ts'
import { usersApi } from '../../api/services.ts'
import { apiClient } from '../../api/client.ts'
import { can, PERMISSION_MATRIX } from '../../lib/permissions.ts'
import type { UserRole } from '../../api/types.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { useUnsavedGuard } from '../../hooks/useUnsavedGuard.ts'
import { useAuth } from '../auth/AuthContext.tsx'

export function CreateUserPage() {
  const nav = useNavigate()
  const { user } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [role, setRole] = useState<UserRole>('OPERATOR')
  const [active, setActive] = useState(true)
  const [buildingId, setBuildingId] = useState('')
  const [buildings, setBuildings] = useState<{ id: string; name: string }[]>([])
  const [show, setShow] = useState(false)
  const [touched, setTouched] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const dirty = !!displayName.trim() || !!username.trim() || !!email.trim() || !!password || !!confirm
  useUnsavedGuard(dirty)
  useEffect(() => { apiClient.get<{ id: string; name: string }[]>('/api/v1/buildings').then(setBuildings).catch(() => setErr('Không tải được tòa nhà.')) }, [])

  const perms = PERMISSION_MATRIX.map((p) => ({
    ...p,
    granted: can({ id: '', username: '', display_name: '', active, role }, p.perm),
  }))

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!displayName.trim() || !username.trim() || !password) { setErr(translate("Vui lòng điền các trường bắt buộc.")); return }
    if (password !== confirm) { setErr(translate("Mật khẩu xác nhận không khớp.")); return }
    if (password.length < 8) { setErr(translate("Mật khẩu tối thiểu 8 ký tự.")); return }
    if (user?.role === 'SYSTEM_ADMIN' && role === 'BUILDING_ADMIN' && !buildingId) { setErr('Chọn tòa nhà cho quản trị tòa nhà.'); return }
    setLoading(true)
    setErr(null)
    try {
      await usersApi.create({ username: username.trim(), display_name: displayName.trim(), email: email.trim() || null, password, role, ...(user?.role === 'SYSTEM_ADMIN' ? { building_id: buildingId || null } : {}), active })
      nav('/admin/users')
    } catch (e2: unknown) {
      if (e2 instanceof ApiError && e2.status === 409) setErr(translate("Tên đăng nhập hoặc email đã tồn tại."))
      else setErr(e2 instanceof Error ? e2.message : translate("Tạo tài khoản thất bại."))
    } finally { setLoading(false) }
  }

  return (
    <div className="data-page">
      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">USER PROVISIONING · VISIONPARK</span>
          <h2>{translate("Tạo tài khoản nhân viên")}</h2>
          <p>{translate("Quản lý tài khoản và vai trò, trạng thái hoạt động và hồ sơ vận hành.")}</p>
        </div>
        <Link to="/admin/users" className="btn btn-secondary">{translate("Hủy")}</Link>
      </section>
      {err ? <Alert variant="error">{err}</Alert> : null}
      <form onSubmit={onSubmit} noValidate className="stack">
        <div className="grid-2" style={{ alignItems: 'start' }}>
          <section className="card card-polished stack">
            <span className="card-kicker">IDENTITY</span>
            <h3 style={{ margin: '0 0 8px' }}>{translate("Thông tin cá nhân")}</h3>
            <Input label={translate("Họ và tên *")} value={displayName} onChange={(e) => setDisplayName(e.target.value)} error={touched && !displayName.trim() ? translate("Không được để trống") : undefined} />
            <Input label={translate("Tên đăng nhập *")} value={username} onChange={(e) => setUsername(e.target.value)} error={touched && !username.trim() ? translate("Không được để trống") : undefined} />
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </section>
          <section className="card card-polished stack">
            <span className="card-kicker">CREDENTIALS</span>
            <h3 style={{ margin: '0 0 8px' }}>{translate("Bảo mật")}</h3>
            <div className="field">
              <label>{translate("Mật khẩu *")}</label>
              <div className="input-with-action">
                <input type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShow((v) => !v)}>{show ? translate("Ẩn") : translate("Hiện")}</button>
              </div>
            </div>
            <Input label={translate("Xác nhận mật khẩu *")} type={show ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} error={touched && password !== confirm ? translate("Không khớp") : undefined} />
          </section>
        </div>
        <section className="card card-polished stack">
          <span className="card-kicker">ROLE & ACCESS</span>
          <h3 style={{ margin: '0 0 8px' }}>{translate("Vai trò")}</h3>
          <div className="form-grid">
            <Select label={translate("Vai trò *")} value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
              <option value="OPERATOR">OPERATOR — Vận hành</option>
              {user?.role === 'SYSTEM_ADMIN' && <option value="SYSTEM_ADMIN">SYSTEM_ADMIN — Quản trị hệ thống</option>}
              {user?.role === 'SYSTEM_ADMIN' && <option value="BUILDING_ADMIN">BUILDING_ADMIN — Quản trị tòa nhà</option>}
              <option value="ACCOUNTANT">ACCOUNTANT — Kế toán</option>
              <option value="TECHNICIAN">TECHNICIAN — Kỹ thuật</option>
            </Select>
            {user?.role === 'SYSTEM_ADMIN' && (
              <Select label="Tòa nhà" value={buildingId} onChange={(e) => setBuildingId(e.target.value)}>
                <option value="">Chưa gán</option>
                {buildings.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
              </Select>
            )}
          </div>
          <div className="perm-list">
            {perms.map((p) => <div key={p.perm} className="perm-row"><span>{translate(p.label)}</span><span>{p.granted ? '✓' : '✗'}</span></div>)}
          </div>
          <label className="checkbox"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />{translate("Kích hoạt tài khoản")}</label>
        </section>
        <div className="row-actions" style={{ justifyContent: 'flex-end' }}>
          <Link to="/admin/users" className="btn">{translate("Hủy")}</Link>
          <Button type="submit" variant="primary" loading={loading}>{translate("Tạo tài khoản")}</Button>
        </div>
      </form>
    </div>
  )
}
