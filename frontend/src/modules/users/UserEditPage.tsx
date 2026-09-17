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
  const [role, setRole] = useState<'ADMIN' | 'OPERATOR'>('OPERATOR')
  const [active, setActive] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const dirty = !!user && (
    displayName !== (user.display_name ?? '') ||
    email !== (user.email ?? '') ||
    role !== user.role ||
    active !== user.active
  )
  useUnsavedGuard(dirty)

  useEffect(() => {
    if (!id) return
    usersApi.get(id).then((u) => { setUser(u); setDisplayName(u.display_name); setEmail(u.email ?? ''); setRole(u.role); setActive(u.active) }).catch(() => setErr('Không tải được người dùng')).finally(() => setLoading(false))
  }, [id])

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr(null); setOk(null)
    try {
      await usersApi.patch(id!, { display_name: displayName.trim(), email: email.trim() || null, role, active } as never)
      setOk('Đã lưu.')
    } catch (e2: unknown) { setErr(e2 instanceof Error ? e2.message : 'Lưu thất bại') }
  }

  if (loading) return <div className="spinner">Đang tải...</div>
  if (!user) return <Alert variant="error">{err ?? 'Không tìm thấy'}</Alert>

  return (
    <div>
      <Breadcrumb items={[{ label: 'Người dùng', to: '/admin/users' }, { label: user.username, to: `/admin/users/${id}` }, { label: 'Chỉnh sửa' }]} />
      <h2>Chỉnh sửa người dùng</h2>
      {err ? <Alert variant="error">{err}</Alert> : null}
      {ok ? <Alert variant="success">{ok}</Alert> : null}
      <form onSubmit={onSave} className="card" style={{ maxWidth: 560 }}>
        <Input label="Username" value={user.username} disabled />
        <Input label="Tên hiển thị *" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        <Input label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Select label="Vai trò" value={role} onChange={(e) => setRole(e.target.value as never)}><option value="ADMIN">ADMIN</option><option value="OPERATOR">OPERATOR</option></Select>
        <label style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 12 }}><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Hoạt động</label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" onClick={() => nav(`/admin/users/${id}`)}>Quay lại</Button>
          <Button type="submit" variant="primary">Lưu</Button>
        </div>
        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <Button type="button" disabled title="Backend API required">Khóa/Mở khóa (Backend API required)</Button>
          <Button type="button" disabled title="Backend API required">Đặt lại mật khẩu (Backend API required)</Button>
        </div>
      </form>
    </div>
  )
}
