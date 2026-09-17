import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../modules/auth/AuthContext.tsx'
import { can } from '../lib/permissions.ts'
import type { Permission } from '../lib/permissions.ts'
import { Breadcrumb } from '../components/ui/Breadcrumb.tsx'
import { healthApi } from '../api/healthApi.ts'
import { getUnreadCount, subscribeNotifications } from '../lib/notifications.ts'

type NavItem = { to: string; label: string; icon: string; perm: Permission }

const NAV: NavItem[] = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: '▣', perm: 'dashboard.read' },
  { to: '/station/scan', label: 'Quét biển số', icon: '◎', perm: 'station.use' },
  { to: '/detections', label: 'Lịch sử nhận diện', icon: '≡', perm: 'detections.read' },
  { to: '/admin/lanes', label: 'Làn xe', icon: '⇆', perm: 'lanes.read' },
  { to: '/admin/users', label: 'Người dùng', icon: '♙', perm: 'users.manage' },
  { to: '/admin/roles', label: 'Vai trò', icon: '◈', perm: 'roles.read' },
  { to: '/admin/permissions', label: 'Phân quyền', icon: '⬡', perm: 'permissions.read' },
  { to: '/admin/alpr', label: 'ALPR', icon: '◉', perm: 'alpr.read' },
  { to: '/admin/audit-logs', label: 'Audit Logs', icon: '☷', perm: 'audit.read' },
  { to: '/admin/errors', label: 'Error Center', icon: '⚠', perm: 'errors.read' },
  { to: '/admin/system', label: 'System Health', icon: '⚙', perm: 'system.read' },
  // Tài khoản — luôn hiện khi có phiên, lọc qua can()
  { to: '/profile', label: 'Thông tin cá nhân', icon: '☺', perm: 'profile.read' },
  { to: '/settings', label: 'Cài đặt', icon: '⬢', perm: 'settings.update' },
  { to: '/help', label: 'Trợ giúp', icon: '?', perm: 'help.read' },
  { to: '/docs', label: 'Docs', icon: '▤', perm: 'docs.read' },
]

const TITLE_MAP: Record<string, string> = {
  '/admin/dashboard': 'Dashboard',
  '/station/scan': 'Quét biển số',
  '/station/scan/fullscreen': 'Toàn màn hình',
  '/detections': 'Lịch sử nhận diện',
  '/admin/lanes': 'Làn xe',
  '/admin/lanes/new': 'Tạo làn xe',
  '/admin/users': 'Người dùng',
  '/admin/users/new': 'Tạo người dùng',
  '/admin/roles': 'Vai trò',
  '/admin/permissions': 'Phân quyền',
  '/admin/alpr': 'ALPR',
  '/admin/alpr/test': 'ALPR Test Lab',
  '/admin/audit-logs': 'Audit Logs',
  '/admin/errors': 'Error Center',
  '/admin/system': 'System Health',
  '/profile': 'Thông tin cá nhân',
  '/settings': 'Cài đặt',
  '/notifications': 'Thông báo',
  '/help': 'Trợ giúp',
  '/docs': 'Docs',
}

function crumbs(pathname: string): { label: string; to?: string }[] {
  const segs = pathname.split('/').filter(Boolean)
  // normalize /detections/:id, /admin/lanes/:id/edit, /admin/users/:id/edit etc.
  const p = '/' + segs.join('/')
  const items: { label: string; to?: string }[] = [{ label: 'VisionPark', to: '/admin/dashboard' }]
  // Accumulate known prefixes
  let cur = ''
  for (let i = 0; i < segs.length; i++) {
    cur += '/' + segs[i]
    // skip bare ids in detail/edit routes — show as "Chi tiết"
    const next = segs[i + 1]
    const isId = next && next.length >= 2 && !['new', 'edit', 'test', 'scan', 'fullscreen'].includes(next) && cur.startsWith('/admin/')
    // simple: title-map lookup, else capitalized segment
    const label = TITLE_MAP[cur] ?? (segs[i] === 'edit' ? 'Chỉnh sửa' : segs[i] === 'new' ? 'Tạo mới' : cur.endsWith('/fullscreen') ? 'Toàn màn hình' : segs[i])
    const isLast = i === segs.length - 1
    if (isId && i === segs.length - 2) {
      items.push({ label: TITLE_MAP[cur] ?? label, to: cur })
      items.push({ label: 'Chi tiết' })
      break
    }
    items.push({ label: String(label), to: isLast ? undefined : cur })
    if (p.startsWith(cur + '/') && TITLE_MAP[p]) {
      // leaf overrides — e.g. /admin/alpr/test already pushed; next loop would push 'test'
      if (cur === '/admin/alpr' && p === '/admin/alpr/test') {
        items.push({ label: 'ALPR Test Lab' })
        break
      }
    }
  }
  if (pathname.startsWith('/detections/') && segs.length === 2) {
    // /detections/:id → Lịch sử / Chi tiết
    return [{ label: 'Lịch sử nhận diện', to: '/detections' }, { label: 'Chi tiết' }]
  }
  return items
}

function Sidebar({
  collapsed,
  mobileOpen,
  onToggle,
  onCloseMobile,
}: {
  collapsed: boolean
  mobileOpen: boolean
  onToggle: () => void
  onCloseMobile: () => void
}) {
  const { user } = useAuth()
  const visible = NAV.filter((it) => can(user ?? null, it.perm))
  const isCollapsed = collapsed && !mobileOpen

  const group = (title: string, list: NavItem[]) => {
    if (!list.length) return null
    return (
      <>
        {!isCollapsed && <div className="sidebar-group">{title}</div>}
        {list.map((it) => (
          <NavLink key={it.to} to={it.to} onClick={onCloseMobile} className={({ isActive }) => (isActive ? 'active' : undefined)}>
            <span className="nav-icon">{it.icon}</span> {!isCollapsed && it.label}
          </NavLink>
        ))}
      </>
    )
  }

  const sidebarInner = (
    <>
      <div className="brand">
        <span>◉ VisionPark</span>
        <button type="button" className="collapse-btn" onClick={onToggle} aria-label="Toggle sidebar">
          {isCollapsed ? '›' : '‹'}
        </button>
      </div>
      <nav>
        {group('TỔNG QUAN', visible.filter((x) => x.to === '/admin/dashboard'))}
        {group('VẬN HÀNH', visible.filter((x) => ['/station/scan', '/detections'].includes(x.to)))}
        {group('QUẢN LÝ', visible.filter((x) => ['/admin/lanes', '/admin/users', '/admin/roles', '/admin/permissions'].includes(x.to)))}
        {group('AI & HỆ THỐNG', visible.filter((x) => ['/admin/alpr', '/admin/audit-logs', '/admin/errors', '/admin/system'].includes(x.to)))}
        {group('TÀI KHOẢN', visible.filter((x) => ['/profile', '/settings', '/help'].includes(x.to)))}
        {group('DEVELOPER', visible.filter((x) => x.to === '/docs'))}
      </nav>
      <div className="sidebar-footer">
        {!isCollapsed && <NavLink to="/profile">Hồ sơ cá nhân</NavLink>}
        {!isCollapsed && (
          <NavLink to="/dev/ui-kit" style={{ fontSize: 12, color: '#9ca3af' }}>
            UI Kit
          </NavLink>
        )}
      </div>
    </>
  )

  if (mobileOpen) {
    return (
      <div className="drawer-overlay" role="presentation" onClick={onCloseMobile}>
        <aside className="admin-sidebar" onClick={(e) => e.stopPropagation()} style={{ height: '100vh', width: 260 }}>
          {sidebarInner}
        </aside>
      </div>
    )
  }
  return <aside className={`admin-sidebar ${isCollapsed ? 'collapsed' : ''}`}>{sidebarInner}</aside>
}

export function AppShell() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [collapsed, setCollapsed] = useState<boolean>(() => localStorage.getItem('vp.sidebarCollapsed') === '1')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [healthOk, setHealthOk] = useState<boolean | null>(null)
  const [unread, setUnread] = useState(getUnreadCount())
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    localStorage.setItem('vp.sidebarCollapsed', collapsed ? '1' : '0')
  }, [collapsed])

  useEffect(() => {
    const unsub = subscribeNotifications(() => setUnread(getUnreadCount()))
    return unsub
  }, [])

  useEffect(() => {
    let alive = true
    healthApi
      .ready()
      .then((h) => {
        if (!alive) return
        const alpr = (h as { alpr?: { ready: boolean } }).alpr
        if (alpr) setHealthOk(alpr.ready)
        else setHealthOk((h.status as string) === 'ok' || (h.status as string) === 'healthy')
      })
      .catch(() => {
        if (alive) setHealthOk(false)
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  // Hide shell on fullscreen route
  if (loc.pathname === '/station/scan/fullscreen') return <Outlet />

  const initial = user ? (user.display_name?.[0] ?? user.username[0]).toUpperCase() : '?'

  return (
    <div className="admin-layout">
      {/* mobile hamburger */}
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={() => setCollapsed((v) => !v)}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="admin-main-wrap">
        <header className="app-header">
          <div className="header-left" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setMobileOpen(true)} aria-label="Mở menu" style={{ display: 'none' }} id="hamburger">
              ☰
            </button>
            <Breadcrumb items={crumbs(loc.pathname)} />
          </div>
          <div className="header-right" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span title={healthOk === null ? 'Đang kiểm tra ALPR...' : healthOk ? 'ALPR sẵn sàng' : 'ALPR không sẵn sàng'} style={{ fontSize: 12, color: 'var(--muted)' }}>
              <span className={`status-dot ${healthOk === null ? 'dot-warn' : healthOk ? 'dot-ok' : 'dot-bad'}`} />
              ALPR
            </span>
            <NavLink to="/notifications" className="notif-wrap btn btn-ghost btn-sm" aria-label="Thông báo">
              🔔{unread > 0 ? <span className="notif-count">{unread > 99 ? '99+' : unread}</span> : null}
            </NavLink>
            <div className="dropdown" ref={menuRef}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setMenuOpen((v) => !v)} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="avatar">{initial}</span>
                <span>
                  {user?.display_name} <small style={{ color: 'var(--muted)' }}>{user?.role}</small>
                </span>
              </button>
              {menuOpen ? (
                <div className="dropdown-menu">
                  <NavLink to="/profile" onClick={() => setMenuOpen(false)}>
                    Hồ sơ cá nhân
                  </NavLink>
                  <NavLink to="/settings" onClick={() => setMenuOpen(false)}>
                    Cài đặt
                  </NavLink>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false)
                      logout()
                      nav('/login')
                    }}
                  >
                    Đăng xuất
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>
        <main className="admin-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
