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
    <div className="utility-page docs-home-page">
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Developer docs · VisionPark</span>
          <h1>Docs Center</h1>
          <p>Tài liệu developer/admin — nguồn thật từ <code>frontend/docs/*.md</code>. Không fake số liệu.</p>
        </div>
        <div className="utility-hero-stat"><strong>{filtered.length}</strong><span>tài liệu</span></div>
      </section>
      <section className="utility-panel utility-health-panel">
        <div className="utility-panel-head">
          <div><span className="utility-section-kicker">LIVE CHECK</span><h3>Trạng thái hệ thống</h3></div>
          <Badge variant={health ? 'success' : 'warning'}>{health ? 'Đang hoạt động' : 'Chưa tải'}</Badge>
        </div>
        {health ? <pre className="code-block">{JSON.stringify(health, null, 2)}</pre> : <p className="muted">Không lấy được /health/ready.</p>}
        <p className="utility-source">Nguồn: GET /health/ready — dữ liệu live, không fake.</p>
      </section>
      <label className="utility-search-label" htmlFor="docs-search">Tìm trong tài liệu</label>
      <input id="docs-search" className="docs-search utility-search" placeholder="Tìm tài liệu..." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm tài liệu" />
      <div className="docs-index-grid">
        {filtered.map((s) => <Link key={s} to={`/docs/${s === 'overview' ? '' : s}`} className="docs-index-card"><span>{s}</span><span aria-hidden="true">→</span></Link>)}
      </div>
      <p className="utility-callout">Gợi ý: mở <code>AGENTS.md</code> tại root để biết quy tắc bootstrap cho agent.</p>
    </div>
  )
}
