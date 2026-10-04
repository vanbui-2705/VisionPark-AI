import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { Badge } from '../../components/ui/Badge.tsx'

const DOCS_LIST = ['overview','architecture','frontend','backend','api','database','auth','rbac','alpr','station','lanes','users','components','routes','configuration','testing','deployment','decisions','changelog','backlog','known-issues','ai-context']

export function DocsHomePage() {
  const [q, setQ] = useState('')
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  useEffect(() => { healthApi.ready().then(setHealth).catch(() => {}) }, [])
  const filtered = useMemo(() => DOCS_LIST.filter((s) => s.includes(q.toLowerCase())), [q])
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Developer Docs · Duy Anh</div>
          <h1 style={{ margin: '6px 0 6px', fontSize: 24, fontWeight: 800 }}>VisionPark — Docs Center</h1>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Tài liệu developer/admin — nguồn thật từ <code>frontend/docs/*.md</code>. Không fake số liệu.</p>
        </div>
        <Badge>{filtered.length} docs</Badge>
      </div>
      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <h3 style={{ marginTop: 0 }}>Trạng thái hệ thống (thật)</h3>
        {health ? <pre className="code-block">{JSON.stringify(health, null, 2)}</pre> : <p className="muted">Không lấy được /health/ready.</p>}
        <p className="muted" style={{ fontSize: 12 }}>Nguồn: GET /health/ready — dữ liệu live, không fake.</p>
      </section>
      <input className="docs-search" placeholder="Tìm tài liệu..." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm tài liệu" />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px,1fr))', gap: 10 }}>
        {filtered.map((s) => <Link key={s} to={`/docs/${s === 'overview' ? '' : s}`} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '12px 14px', textDecoration: 'none', color: 'var(--text)', fontWeight: 700, boxShadow: '0 4px 14px rgba(15,23,42,0.05)' }}>{s}</Link>)}
      </div>
      <div className="callout">Gợi ý: mở <code>AGENTS.md</code> tại root để biết quy tắc bootstrap cho agent.</div>
    </div>
  )
}
