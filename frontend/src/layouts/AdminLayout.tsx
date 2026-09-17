import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../modules/auth/AuthContext.tsx'

export function AdminLayout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="brand">VisionPark</div>
        <nav>
          <NavLink to="/admin/lanes">Quản lý làn</NavLink>
          <NavLink to="/station">Station</NavLink>
        </nav>
        <div className="admin-user">
          <div>{user?.display_name}</div>
          <div>{user?.role}</div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginTop: 8 }}
            onClick={() => {
              logout()
              nav('/login')
            }}
          >
            Đăng xuất
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  )
}
