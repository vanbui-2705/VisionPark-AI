import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { usersApi } from '../../api/services.ts'
import type { ManagedUser } from '../../api/domain.ts'
import { can, PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { apiClient } from '../../api/client'
import { auditApi } from '../../api/services'
import type { AuditLog } from '../../api/domain'

export function UserDetailPage() {
  const { id } = useParams()
  const [user, setUser] = useState<ManagedUser | null>(null)
  const [tab, setTab] = useState<'info'|'perm'|'security'|'activity'>('info')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<ManagedUser['role']>('OPERATOR')
  const [active, setActive] = useState(true)
  const [audit, setAudit] = useState<AuditLog[]>([])
  const [securityMessage, setSecurityMessage] = useState('')
  useEffect(() => {
    if (id && tab === 'activity') auditApi.list({ actor_id: id, limit: 50 }).then(setAudit).catch(e => setErr(e.message))
  }, [id, tab])

  useEffect(() => {
    if (!id) return
    usersApi.get(id).then(u => { setUser(u); setDisplayName(u.display_name); setEmail(u.email ?? ''); setRole(u.role); setActive(u.active)}).catch(e=>setErr(e instanceof Error?e.message:translate("Không tải được user"))).finally(()=>setLoading(false))
  }, [id])

  const onSave = async () => {
    if (!id || !user) return
    setSaving(true); setErr(null)
    try { const u = await usersApi.patch(id, { display_name: displayName, email: email || null, role, active }); setUser(u) } catch(e){ setErr(e instanceof Error?e.message:translate("Lưu thất bại"))} finally { setSaving(false)}
  }

  if (loading) return <Spinner />
  if (err && !user) return <Alert variant="error">{err}</Alert>
  if (!user) return <Alert variant="info">{translate("Không tìm thấy user.")}</Alert>

  return (
    <div>
      <Link to="/admin/users">{translate("← Danh sách")}</Link>
      <h2 style={{marginTop:8}}>{user.display_name} — {user.username}</h2>
      <div className="tabs">
        <button className={tab==='info'?'active':''} onClick={()=>setTab('info')}>{translate("Thông tin")}</button>
        <button className={tab==='perm'?'active':''} onClick={()=>setTab('perm')}>{translate("Phân quyền")}</button>
        <button className={tab==='security'?'active':''} onClick={()=>setTab('security')}>{translate("Bảo mật")}</button>
        <button className={tab==='activity'?'active':''} onClick={()=>setTab('activity')}>{translate("Hoạt động")}</button>
      </div>
      {err ? <Alert variant="error">{err}</Alert>:null}
      {tab==='info' && (
        <section className="card">
          <Input label="Display Name" value={displayName} onChange={e=>setDisplayName(e.target.value)} />
          <Input label="Email" value={email} onChange={e=>setEmail(e.target.value)} />
          <Select label="Role" value={role} onChange={e=>setRole(e.target.value as ManagedUser['role'])}><option value="OPERATOR">OPERATOR</option><option value="ADMIN">ADMIN</option><option value="ACCOUNTANT">ACCOUNTANT</option><option value="TECHNICIAN">TECHNICIAN</option></Select>
          <label className="checkbox"><input type="checkbox" checked={active} onChange={e=>setActive(e.target.checked)} /> Active</label>
          <p className="muted">Username: {user.username} — ID: {user.id}</p>
          <Button onClick={onSave} loading={saving}>{translate("Lưu")}</Button>
        </section>
      )}
      {tab==='perm' && (
        <section className="card">
          <h3>Permission matrix — {role}</h3>
          <table className="table"><thead><tr><th>{translate("Chức năng")}</th><th>{translate("Quyền")}</th></tr></thead><tbody>{PERMISSION_MATRIX.map(p=> <tr key={p.perm}><td>{translate(p.label)}</td><td>{can({ ...user, role }, p.perm)?'✓':'✗'}</td></tr>)}</tbody></table>
          <p className="muted">{translate("Quyền theo vai trò được thực thi tại backend.")}</p>
        </section>
      )}
      {tab==='security' && (
        <section className="card">
          <h3>{translate("Bảo mật")}</h3>
          <Link className="btn" to={`/admin/users/${id}/edit`}>{translate("Đổi mật khẩu / khóa tài khoản")}</Link>
          <Button variant="secondary" disabled={saving} style={{marginLeft:8}} onClick={async () => {
            setSaving(true); setErr(null); setSecurityMessage('');
            try { await apiClient.post(`/api/v1/users/${id}/revoke-sessions`); setSecurityMessage(translate("Đã thu hồi các phiên đăng nhập.")); }
            catch (e) { setErr(e instanceof Error ? e.message : translate("Thu hồi thất bại.")); }
            finally { setSaving(false); }
          }}>Force Logout</Button>
          {securityMessage && <p role="status">{securityMessage}</p>}
        </section>
      )}
      {tab==='activity' && (
        <section className="card">
          <h3>{translate("Hoạt động")}</h3>
          <p className="muted">Last login: {user.last_login ?? '—'} — Created: {user.created_at ?? '—'}</p>
          {audit.length ? <ul>{audit.map(a => <li key={a.id}>{new Date(a.time).toLocaleString()} · {a.action} · {a.resource}</li>)}</ul> : <p>{translate("Chưa có nhật ký hoạt động.")}</p>}
        </section>
      )}
    </div>
  )
}
