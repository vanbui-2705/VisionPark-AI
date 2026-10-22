import { t as translate } from "../../lib/i18n"
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { usersApi } from '../../api/services.ts'
import type { ManagedUser } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Table } from '../../components/ui/Table.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'

export function UserListPage() {
  const [users, setUsers] = useState<ManagedUser[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [role, setRole] = useState('ALL')
  const [status, setStatus] = useState('ALL')

  const load = async () => {
    setLoading(true)
    setErr(null)
    try {
      const data = await usersApi.list()
      setUsers(data)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : translate("Tải danh sách thất bại."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const filtered = useMemo(() => {
    if (!users) return []
    return users.filter((u) => {
      if (role !== 'ALL' && u.role !== role) return false
      if (status === 'ACTIVE' && !u.active) return false
      if (status === 'INACTIVE' && u.active) return false
      if (q) {
        const hay = `${u.username} ${u.display_name} ${u.email ?? ''}`.toLowerCase()
        if (!hay.includes(q.toLowerCase())) return false
      }
      return true
    })
  }, [users, q, role, status])

  if (loading) return <Spinner />
  if (err) return <div><Alert variant="error">{err}</Alert><Button onClick={() => void load()}>{translate("Thử lại")}</Button></div>

  return (
    <div className="data-page users-page">
      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">User Management · Duy Anh</span>
          <h2>{translate("Người dùng")}</h2>
          <p>{translate("Quản lý tài khoản và vai trò, trạng thái hoạt động và hồ sơ vận hành.")}</p>
        </div>
        <Link to="/admin/users/new" className="btn btn-secondary">{translate("+ Tạo tài khoản")}</Link>
      </section>

      <section className="data-filter-card data-filter-card--compact">
        <span className="data-section-kicker">{translate("Bộ lọc tài khoản")}</span>
        <div className="data-filter-grid data-filter-grid--users">
          <Input label={translate("Tìm kiếm")} value={q} onChange={(e) => setQ(e.target.value)} placeholder={translate("Tên / username / email")} />
          <Select label={translate("Vai trò")} value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="ALL">ALL</option>
            <option value="SYSTEM_ADMIN">SYSTEM_ADMIN</option>
            <option value="OPERATOR">OPERATOR</option>
            <option value="ACCOUNTANT">ACCOUNTANT</option>
            <option value="TECHNICIAN">TECHNICIAN</option>
          </Select>
          <Select label={translate("Trạng thái")} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="ALL">ALL</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </Select>
        </div>
      </section>

      {filtered.length === 0 ? <EmptyState title={translate("Không có người dùng phù hợp")} /> : (
        <section className="data-table-card">
          <div className="data-table-head">
            <div>
              <span className="data-section-kicker">DANH BẠ NHÂN SỰ</span>
              <h3>{translate("Danh sách tài khoản")}</h3>
            </div>
            <span className="data-table-meta">{filtered.length} / {users?.length ?? 0}</span>
          </div>
          <Table>
            <thead><tr><th>Username</th><th>{translate("Họ tên")}</th><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id}>
                  <td className="data-mono"><strong>{u.username}</strong></td>
                  <td>{u.display_name}</td>
                  <td>{u.email ?? '—'}</td>
                  <td><span className={`badge ${u.role === 'SYSTEM_ADMIN' ? 'badge-info' : u.role === 'ACCOUNTANT' ? 'badge-success' : u.role === 'TECHNICIAN' ? 'badge-warn' : 'badge-muted'}`}>{u.role}</span></td>
                  <td><span className={`badge ${u.active ? 'badge-success' : 'badge-muted'}`}>{u.active ? 'Active' : 'Locked'}</span></td>
                  <td><Link to={`/admin/users/${u.id}`} className="data-inline-action">{translate("Sửa")}</Link></td>
                </tr>
              ))}
            </tbody>
          </Table>
        </section>
      )}
    </div>
  )
}
