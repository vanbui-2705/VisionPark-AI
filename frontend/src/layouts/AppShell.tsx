import { t as translate } from "../lib/i18n"
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../modules/auth/AuthContext.tsx'
import { can } from '../lib/permissions.ts'
import type { Permission } from '../lib/permissions.ts'
import { Breadcrumb } from '../components/ui/Breadcrumb.tsx'
import { healthApi } from '../api/healthApi.ts'
import { getUnreadCount, subscribeNotifications } from '../lib/notifications.ts'

type NavItem = { to: string; label: string; icon: string; perm: Permission }

function SidebarIcon({ to, fallback }: { to: string; fallback: string }) {
  switch (to) {
    case '/admin/dashboard':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="9" rx="2" /><rect x="14" y="3" width="7" height="5" rx="2" /><rect x="14" y="12" width="7" height="9" rx="2" /><rect x="3" y="16" width="7" height="5" rx="2" /></svg>
    case '/station/scan':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><rect x="7" y="9" width="10" height="6" rx="1.5" /><path d="M10 12h4" /></svg>
    case '/detections':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5M8 11h6M11 8v6" /></svg>
    case '/parking':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9.5 16V8h3.2a2.5 2.5 0 0 1 0 5H9.5" /></svg>
    case '/admin/lanes':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19 8 5M20 19 16 5M12 5v3M12 11v3M12 17v2" /></svg>
    case '/admin/users':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="3.5" /><path d="M3.5 19a5.5 5.5 0 0 1 11 0M16 7a3 3 0 0 1 0 6M16.5 19a4.5 4.5 0 0 1 4-4.4" /></svg>
    case '/admin/roles':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4 7v5c0 5 3.4 8.8 8 10 4.6-1.2 8-5 8-10V7l-8-4Z" /><path d="m9 12 2 2 4-4" /></svg>
    case '/admin/permissions':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="15" r="4" /><path d="m10.8 12.2 8.2-8.2M16 7l3 3M18 4l2 2" /></svg>
    case '/admin/alpr':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="3" /><rect x="9" y="9" width="6" height="6" rx="1" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2" /></svg>
    case '/admin/audit-logs':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" /></svg>
    case '/admin/errors':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></svg>
    case '/admin/system':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 12h-4l-3 7L9 5l-3 7H2" /></svg>
    case '/profile':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>
    case '/settings':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.77 1.02 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" /></svg>
    case '/help':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4M12 17h.01" /></svg>
    case '/docs':
      return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></svg>
    default:
      return <>{fallback}</>
  }
}

const NAV: NavItem[] = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: '▣', perm: 'dashboard.read' },
  { to: '/station/scan', label: 'Quét biển số', icon: '◎', perm: 'station.use' },
  { to: '/detections', label: 'Lịch sử nhận diện', icon: '≡', perm: 'detections.read' },
  { to: '/parking', label: 'Lịch sử đỗ xe', icon: '▤', perm: 'transactions.read' },
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
    const label = TITLE_MAP[cur] ?? (segs[i] === 'edit' ? translate("Chỉnh sửa") : segs[i] === 'new' ? translate("Tạo mới") : cur.endsWith('/fullscreen') ? translate("Toàn màn hình") : segs[i])
    const isLast = i === segs.length - 1
    if (isId && i === segs.length - 2) {
      items.push({ label: TITLE_MAP[cur] ?? label, to: cur })
      items.push({ label: translate("Chi tiết") })
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
    return [{ label: translate("Lịch sử nhận diện"), to: '/detections' }, { label: translate("Chi tiết") }]
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
            <span className="nav-icon" aria-hidden="true"><SidebarIcon to={it.to} fallback={it.icon} /></span> {!isCollapsed && it.label}
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
        {group(translate("TỔNG QUAN"), visible.filter((x) => x.to === '/admin/dashboard'))}
        {group(translate("VẬN HÀNH"), visible.filter((x) => ['/station/scan', '/detections', '/parking'].includes(x.to)))}
        {group(translate("QUẢN LÝ"), visible.filter((x) => ['/admin/lanes', '/admin/users', '/admin/roles', '/admin/permissions'].includes(x.to)))}
        {group(translate("AI & HỆ THỐNG"), visible.filter((x) => ['/admin/alpr', '/admin/audit-logs', '/admin/errors', '/admin/system'].includes(x.to)))}
        {group(translate("TÀI KHOẢN"), visible.filter((x) => ['/profile', '/settings', '/help'].includes(x.to)))}
        {group('DEVELOPER', visible.filter((x) => x.to === '/docs'))}
      </nav>
      <div className="sidebar-footer">
        {!isCollapsed && <NavLink to="/profile">{translate("Hồ sơ cá nhân")}</NavLink>}
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
          <div className="header-left">
            <button type="button" className="header-menu-button btn btn-ghost btn-sm" onClick={() => setMobileOpen(true)} aria-label={translate("Mở menu")} id="hamburger">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
            </button>
            <Breadcrumb items={crumbs(loc.pathname)} />
          </div>
          <div className="header-right">
            <span className="header-status" title={healthOk === null ? translate("Đang kiểm tra ALPR...") : healthOk ? translate("ALPR sẵn sàng") : translate("ALPR không sẵn sàng")}>
              <span className={`status-dot ${healthOk === null ? 'dot-warn' : healthOk ? 'dot-ok' : 'dot-bad'}`} />
              ALPR
            </span>
            <NavLink to="/notifications" className="notif-wrap header-icon-button btn btn-ghost btn-sm" aria-label={translate("Thông báo")}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg>
              {unread > 0 ? <span className="notif-count">{unread > 99 ? '99+' : unread}</span> : null}
            </NavLink>
            <div className="dropdown" ref={menuRef}>
              <button type="button" className={`profile-trigger btn btn-ghost btn-sm${menuOpen ? ' is-open' : ''}`} onClick={() => setMenuOpen((v) => !v)} aria-expanded={menuOpen}>
                <span className="avatar">{initial}</span>
                <span className="profile-copy">
                  <strong>{user?.display_name}</strong>
                  <small>{user?.role}</small>
                </span>
                <svg className="profile-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5" /></svg>
              </button>
              {menuOpen ? (
                <div className="dropdown-menu">
                  <NavLink to="/profile" onClick={() => setMenuOpen(false)}>{translate("Hồ sơ cá nhân")}</NavLink>
                  <NavLink to="/settings" onClick={() => setMenuOpen(false)}>{translate("Cài đặt")}</NavLink>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false)
                      logout()
                      nav('/login')
                    }}
                  >{translate("Đăng xuất")}</button>
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
