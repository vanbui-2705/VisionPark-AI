import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { usersApi } from '../../api/services.ts'
import type { ManagedUser } from '../../api/domain.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { useUnsavedGuard } from '../../hooks/useUnsavedGuard.ts'

export function UserEditPage() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [user, setUser] = useState<ManagedUser | null>(null)
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<ManagedUser['role']>('OPERATOR')
  const [active, setActive] = useState(true)
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const dirty = !!user && (
    displayName !== (user.display_name ?? '') ||
    email !== (user.email ?? '') ||
    role !== user.role ||
    active !== user.active || !!password
  )
  useUnsavedGuard(dirty)

  useEffect(() => {
    if (!id) return
    usersApi.get(id).then((u) => { setUser(u); setDisplayName(u.display_name); setEmail(u.email ?? ''); setRole(u.role); setActive(u.active) }).catch(() => setErr(translate("Không tải được người dùng"))).finally(() => setLoading(false))
  }, [id])

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr(null); setOk(null)
    if (password && password.length < 8) { setErr(translate("Mật khẩu tối thiểu 8 ký tự.")); return }
    setSaving(true)
    try {
      const updated = await usersApi.patch(id!, { display_name: displayName.trim(), email: email.trim() || null, role, active, ...(password ? { password } : {}) })
      setUser(updated)
      setDisplayName(updated.display_name)
      setEmail(updated.email ?? '')
      setPassword('')
      setOk(translate("Đã lưu."))
    } catch (e2: unknown) { setErr(e2 instanceof Error ? e2.message : translate("Lưu thất bại")) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="spinner">{translate("Đang tải...")}</div>
  if (!user) return <Alert variant="error">{err ?? translate("Không tìm thấy")}</Alert>

  return (
    <div>
      <Breadcrumb items={[{ label: translate("Người dùng"), to: '/admin/users' }, { label: user.username, to: `/admin/users/${id}` }, { label: translate("Chỉnh sửa") }]} />
      <h2>{translate("Chỉnh sửa người dùng")}</h2>
      {err ? <Alert variant="error">{err}</Alert> : null}
      {ok ? <Alert variant="success">{ok}</Alert> : null}
      <form onSubmit={onSave} className="card" style={{ maxWidth: 560 }}>
        <Input label="Username" value={user.username} disabled />
        <Input label={translate("Tên hiển thị *")} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        <Input label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input label={translate("Mật khẩu mới (để trống nếu giữ nguyên)")} type="password" autoComplete="new-password" value={password} minLength={8} maxLength={128} onChange={(e) => setPassword(e.target.value)} />
        <Select label={translate("Vai trò")} value={role} onChange={(e) => setRole(e.target.value as ManagedUser['role'])}>
          <option value="ADMIN">ADMIN — Quản trị</option>
          <option value="OPERATOR">OPERATOR — Vận hành</option>
          <option value="ACCOUNTANT">ACCOUNTANT — Kế toán</option>
          <option value="TECHNICIAN">TECHNICIAN — Kỹ thuật</option>
        </Select>
        <label style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 12 }}>
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          {translate("Hoạt động")}
        </label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" onClick={() => nav(`/admin/users/${id}`)}>{translate("Quay lại")}</Button>
          <Button type="submit" variant="primary" loading={saving}>{translate("Lưu")}</Button>
        </div>
      </form>
    </div>
  )
}
