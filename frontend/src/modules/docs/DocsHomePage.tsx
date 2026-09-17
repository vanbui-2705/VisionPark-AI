import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'

const DOCS_LIST = ['overview','architecture','frontend','backend','api','database','auth','rbac','alpr','station','lanes','users','components','routes','configuration','testing','deployment','decisions','changelog','backlog','known-issues','ai-context']

export function DocsHomePage() {
  const [q, setQ] = useState('')
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  useEffect(() => { healthApi.ready().then(setHealth).catch(() => {}) }, [])
  const filtered = useMemo(() => DOCS_LIST.filter((s) => s.includes(q.toLowerCase())), [q])
  return (
    <div>
      <h1>VisionPark — Docs Center</h1>
      <p className="muted">Tài liệu developer/admin — nguồn thật từ <code>frontend/docs/*.md</code>. Không fake số liệu.</p>
      <div className="card" style={{ marginBottom: 12 }}>
        <h3>Trạng thái hệ thống (thật)</h3>
        {health ? <pre className="code-block">{JSON.stringify(health, null, 2)}</pre> : <p className="muted">Không lấy được /health/ready.</p>}
        <p className="muted" style={{ fontSize: 12 }}>Nguồn: GET /health/ready — dữ liệu live, không fake.</p>
      </div>
      <input className="docs-search" placeholder="Tìm tài liệu..." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm tài liệu" />
      <ul style={{ marginTop: 12 }}>
        {filtered.map((s) => <li key={s}><Link to={`/docs/${s === 'overview' ? '' : s}`}>{s}</Link></li>)}
      </ul>
      <div className="callout">Gợi ý: mở <code>AGENTS.md</code> tại root để biết quy tắc bootstrap cho agent.</div>
    </div>
  )
}
