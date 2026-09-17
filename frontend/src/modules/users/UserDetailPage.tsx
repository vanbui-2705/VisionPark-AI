import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { usersApi } from '../../api/services.ts'
import type { ManagedUser } from '../../api/domain.ts'
import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'

export function UserDetailPage() {
  const { id } = useParams()
  const [user, setUser] = useState<ManagedUser | null>(null)
  const [tab, setTab] = useState<'info'|'perm'|'security'|'activity'>('info')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'ADMIN'|'OPERATOR'>('OPERATOR')
  const [active, setActive] = useState(true)

  useEffect(() => {
    if (!id) return
    usersApi.get(id).then(u => { setUser(u); setDisplayName(u.display_name); setEmail(u.email ?? ''); setRole(u.role); setActive(u.active)}).catch(e=>setErr(e instanceof Error?e.message:'Không tải được user')).finally(()=>setLoading(false))
  }, [id])

  const onSave = async () => {
    if (!id || !user) return
    setSaving(true); setErr(null)
    try { const u = await usersApi.patch(id, { display_name: displayName, email: email || null, role, active }); setUser(u) } catch(e){ setErr(e instanceof Error?e.message:'Lưu thất bại — P1-FE-USER-API pending')} finally { setSaving(false)}
  }

  if (loading) return <Spinner />
  if (err && !user) return <Alert variant="error">{err}</Alert>
  if (!user) return <Alert variant="info">Không tìm thấy user.</Alert>

  return (
    <div>
      <Link to="/admin/users">← Danh sách</Link>
      <h2 style={{marginTop:8}}>{user.display_name} — {user.username}</h2>
      <div className="tabs">
        <button className={tab==='info'?'active':''} onClick={()=>setTab('info')}>Thông tin</button>
        <button className={tab==='perm'?'active':''} onClick={()=>setTab('perm')}>Phân quyền</button>
        <button className={tab==='security'?'active':''} onClick={()=>setTab('security')}>Bảo mật</button>
        <button className={tab==='activity'?'active':''} onClick={()=>setTab('activity')}>Hoạt động</button>
      </div>
      {err ? <Alert variant="error">{err}</Alert>:null}
      {tab==='info' && (
        <section className="card">
          <Input label="Display Name" value={displayName} onChange={e=>setDisplayName(e.target.value)} />
          <Input label="Email" value={email} onChange={e=>setEmail(e.target.value)} />
          <Select label="Role" value={role} onChange={e=>setRole(e.target.value as never)}><option value="OPERATOR">OPERATOR</option><option value="ADMIN">ADMIN</option></Select>
          <label className="checkbox"><input type="checkbox" checked={active} onChange={e=>setActive(e.target.checked)} /> Active</label>
          <p className="muted">Username: {user.username} — ID: {user.id}</p>
          <Button onClick={onSave} loading={saving}>Lưu</Button>
        </section>
      )}
      {tab==='perm' && (
        <section className="card">
          <h3>Permission matrix — {role}</h3>
          <table className="table"><thead><tr><th>Chức năng</th><th>Quyền</th></tr></thead><tbody>{PERMISSION_MATRIX.map(p=> <tr key={p.perm}><td>{p.label}</td><td>{(role==='ADMIN'?p.admin:p.operator)?'✓':'✗'}</td></tr>)}</tbody></table>
          <p className="muted">Readonly theo role — Phase 1 chỉ 2 role.</p>
        </section>
      )}
      {tab==='security' && (
        <section className="card">
          <h3>Bảo mật</h3>
          <Button variant="secondary" disabled>Reset Password — Chức năng chờ Backend API</Button>
          <Button variant="secondary" disabled style={{marginLeft:8}}>Force Logout — Chức năng chờ Backend API</Button>
        </section>
      )}
      {tab==='activity' && (
        <section className="card">
          <h3>Hoạt động</h3>
          <p className="muted">Last login: {user.last_login ?? '—'} — Created: {user.created_at ?? '—'}</p>
          <p className="muted">Recent audit logs sẽ hiện khi /audit-logs có filter theo user.</p>
        </section>
      )}
    </div>
  )
}
