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
      setErr(e instanceof Error ? e.message : 'Tải danh sách thất bại. (P1-FE-USER-API pending)')
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
  if (err) return <div><Alert variant="error">{err}</Alert><Button onClick={() => void load()}>Thử lại</Button></div>

  return (
    <div className="data-page users-page">
      <section className="data-hero data-hero--cream">
        <div className="data-hero-copy">
          <span className="data-kicker">WORKFORCE · VISIONPARK</span>
          <h2>Người dùng</h2>
          <p>Quản lý tài khoản quản trị, nhân viên vận hành và trạng thái truy cập.</p>
        </div>
        <Link to="/admin/users/new" className="btn btn-primary">+ Tạo tài khoản</Link>
      </section>
      <section className="data-filter-card data-filter-card--compact">
        <div className="data-section-kicker">Bộ lọc tài khoản</div>
        <div className="data-filter-grid data-filter-grid--users">
        <Input label="Tìm kiếm" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tên / username / email" />
        <Select label="Vai trò" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="ALL">Tất cả</option>
          <option value="ADMIN">ADMIN</option>
          <option value="OPERATOR">OPERATOR</option>
          <option value="ACCOUNTANT">ACCOUNTANT</option>
          <option value="TECHNICIAN">TECHNICIAN</option>
        </Select>
        <Select label="Trạng thái" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="ALL">Tất cả</option>
          <option value="ACTIVE">Đang hoạt động</option>
          <option value="INACTIVE">Không hoạt động</option>
        </Select>
        </div>
      </section>
      {filtered.length === 0 ? <EmptyState title="Không có người dùng phù hợp" /> : (
        <section className="data-table-card">
          <div className="data-table-head">
            <div><span className="data-section-kicker">ACCESS DIRECTORY</span><h3>Danh sách người dùng</h3></div>
            <span className="data-table-meta">{filtered.length} tài khoản</span>
          </div>
          <Table>
          <thead><tr><th>Tên đăng nhập</th><th>Họ tên</th><th>Email</th><th>Vai trò</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.display_name}</td>
                <td>{u.email ?? '—'}</td>
                <td><span className={`badge ${u.role === 'ADMIN' ? 'badge-info' : u.role === 'ACCOUNTANT' ? 'badge-success' : u.role === 'TECHNICIAN' ? 'badge-warn' : 'badge-muted'}`}>{u.role}</span></td>
                <td><span className={`badge ${u.active ? 'badge-success' : 'badge-muted'}`}>{u.active ? 'Đang hoạt động' : 'Đã khóa'}</span></td>
                <td><Link className="data-inline-action" to={`/admin/users/${u.id}`}>Sửa</Link></td>
              </tr>
            ))}
          </tbody>
          </Table>
        </section>
      )}
    </div>
  )
}
