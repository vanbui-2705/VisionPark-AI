import { Outlet, NavLink, useNavigate } from 'react-router-dom'
const DOCS = [
  { group: 'Tổng quan', items: [{ slug: '', label: 'Overview' }, { slug: 'architecture', label: 'Architecture' }, { slug: 'ai-context', label: 'AI Context' }] },
  { group: 'Sản phẩm', items: [{ slug: 'frontend', label: 'Frontend' }, { slug: 'backend', label: 'Backend' }, { slug: 'api', label: 'API' }, { slug: 'database', label: 'Database' }, { slug: 'auth', label: 'Auth' }, { slug: 'rbac', label: 'RBAC' }, { slug: 'alpr', label: 'ALPR' }, { slug: 'station', label: 'Station' }, { slug: 'lanes', label: 'Lanes' }, { slug: 'users', label: 'Users' }, { slug: 'components', label: 'Components' }, { slug: 'routes', label: 'Routes' }, { slug: 'configuration', label: 'Configuration' }] },
  { group: 'Vận hành', items: [{ slug: 'testing', label: 'Testing' }, { slug: 'deployment', label: 'Deployment' }] },
  { group: 'Quyết định', items: [{ slug: 'decisions', label: 'Decisions' }, { slug: 'changelog', label: 'Changelog' }, { slug: 'backlog', label: 'Backlog' }, { slug: 'known-issues', label: 'Known Issues' }] },
]
export function DocsLayout() {
  const nav = useNavigate()
  return (
    <div className="docs-layout">
      <aside className="docs-sidebar">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><b>Docs Center</b><button className="btn btn-ghost btn-sm" onClick={() => nav('/admin/dashboard')}>← Admin</button></div>
        <p className="muted" style={{ fontSize: 12 }}>Nguồn: <code>frontend/docs/*.md</code></p>
        {DOCS.map((g) => (
          <div key={g.group}>
            <div className="docs-group">{g.group}</div>
            {g.items.map((it) => (
              <NavLink key={it.slug} to={it.slug ? `/docs/${it.slug}` : '/docs'} end={it.slug === ''} className={({ isActive }) => (isActive ? 'active' : undefined)}>{it.label}</NavLink>
            ))}
          </div>
        ))}
      </aside>
      <div className="docs-content"><Outlet /></div>
    </div>
  )
}
