import { t as translate } from "../../lib/i18n"
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
    <div className="utility-page">
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Developer Docs · Duy Anh</span>
          <h1>VisionPark — Docs Center</h1>
          <p>{translate("Tài liệu developer/admin — nguồn thật từ")} <code>frontend/docs/*.md</code>{translate(". Không fake số liệu.")}</p>
        </div>
        <div className="utility-hero-stat">
          <strong>{filtered.length}</strong>
          <span>docs</span>
        </div>
      </section>
      <section className="utility-panel utility-health-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">LIVE READINESS</span>
            <h3>{translate("Trạng thái hệ thống (thật)")}</h3>
          </div>
          <Badge>{filtered.length} docs</Badge>
        </div>
        {health ? <pre className="code-block">{JSON.stringify(health, null, 2)}</pre> : <p className="muted">{translate("Không lấy được /health/ready.")}</p>}
        <p className="utility-source">{translate("Nguồn: GET /health/ready — dữ liệu live, không fake.")}</p>
      </section>
      <input className="docs-search utility-search" placeholder={translate("Tìm tài liệu...")} value={q} onChange={(e) => setQ(e.target.value)} aria-label={translate("Tìm tài liệu")} />
      <div className="docs-index-grid">
        {filtered.map((s) => <Link key={s} to={`/docs/${s === 'overview' ? '' : s}`} className="docs-index-card"><span>{s}</span><span>→</span></Link>)}
      </div>
      <div className="utility-callout">{translate("Gợi ý: mở")} <code>AGENTS.md</code> {translate("tại root để biết quy tắc bootstrap cho agent.")}</div>
    </div>
  )
}
