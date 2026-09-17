import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'

const ORDER = ['overview','architecture','frontend','backend','api','database','auth','rbac','alpr','station','lanes','users','components','routes','configuration','testing','deployment','decisions','changelog','backlog','known-issues','ai-context']

// slug -> tên file chuẩn UPPERCASE trong docs/ (PROJECT_CONTEXT-style canonical naming)
const canonicalFile = (slug: string) => slug.toUpperCase().replaceAll('-', '_') + '.md'

const rawModules = import.meta.glob('../../../docs/*.md', { query: '?raw', import: 'default' }) as Record<string, () => Promise<string>>

// Very small markdown renderer — đủ heading/para/list/table/code; code block có Copy.
function renderMarkdown(md: string): string {
  const esc = (s: string) => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')
  const lines = md.split('\n')
  let out = ''
  let inCode = false
  let codeBuf = ''
  let codeLang = ''
  let inTable = false
  let tableBuf: string[] = []
  const flushTable = () => {
    if (!tableBuf.length) return
    const rows = tableBuf.map((r) => r.split('|').map((c) => c.trim()).filter(Boolean))
    out += '<table><thead><tr>' + rows[0].map((c) => `<th>${esc(c)}</th>`).join('') + '</tr></thead>'
    if (rows.length > 2) out += '<tbody>' + rows.slice(2).map((r) => '<tr>' + r.map((c) => `<td>${esc(c)}</td>`).join('') + '</tr>').join('') + '</tbody>'
    out += '</table>'
    tableBuf = []; inTable = false
  }
  for (const line of lines) {
    if (line.startsWith('```')) {
      if (!inCode) { inCode = true; codeLang = line.slice(3).trim(); codeBuf = '' }
      else { out += `<pre><code class="language-${esc(codeLang)}">${esc(codeBuf)}</code></pre>`; inCode = false }
      continue
    }
    if (inCode) { codeBuf += line + '\n'; continue }
    if (line.match(/^\|.*\|$/)) { tableBuf.push(line); inTable = true; continue }
    if (inTable && !line.trim()) { flushTable(); continue }
    if (inTable && line.trim() && !line.startsWith('|')) { flushTable() }
    if (line.startsWith('# ')) out += `<h1>${esc(line.slice(2))}</h1>`
    else if (line.startsWith('## ')) out += `<h2>${esc(line.slice(3))}</h2>`
    else if (line.startsWith('### ')) out += `<h3>${esc(line.slice(4))}</h3>`
    else if (line.startsWith('- ') || line.startsWith('* ')) out += `<li>${esc(line.slice(2))}</li>`
    else if (line.match(/^\d+\.\s/)) out += `<li>${esc(line.replace(/^\d+\.\s/,''))}</li>`
    else if (!line.trim()) out += ''
    else out += `<p>${esc(line)}</p>`
  }
  if (inTable) flushTable()
  return out
}

const ALIAS: Record<string, string> = { 'project-context': 'overview' }

export function DocsArticlePage() {
  const { slug } = useParams()
  const nav = useNavigate()
  const rawKey = (slug ?? 'overview').toLowerCase()
  const key = ALIAS[rawKey] ?? rawKey
  const fileKey = `../../../docs/${canonicalFile(key)}`
  const [md, setMd] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  useEffect(() => { healthApi.ready().then(setHealth).catch(() => {}) }, [])
  useEffect(() => {
    setMd(null); setErr(null)
    const loader = rawModules[fileKey]
    if (!loader) { setErr(`Không tìm thấy docs/${canonicalFile(key)}`); return }
    loader().then(setMd).catch((e: Error) => setErr(e.message))
  }, [fileKey, key])

  const idx = ORDER.indexOf(key === 'overview' ? 'overview' : key)
  const prev = idx > 0 ? ORDER[idx - 1] : null
  const next = idx >= 0 && idx < ORDER.length - 1 ? ORDER[idx + 1] : null
  const html = useMemo(() => (md ? renderMarkdown(md) : ''), [md])

  if (err) return <div><h1>{key}</h1><div className="alert alert-error">{err}</div><p className="muted">Source: docs/{canonicalFile(key)}</p><Link to="/docs">← Docs</Link></div>
  if (md == null) return <div style={{ padding: 24 }}>Đang tải docs...</div>

  return (
    <div>
      <div className="muted" style={{ fontSize: 12 }}>Source: <code>docs/{canonicalFile(key)}</code> · <Link to="/docs">Docs index</Link></div>
      {/* eslint-disable-next-line react/no-danger */}
      <div dangerouslySetInnerHTML={{ __html: html }} />
      {key === 'overview' && health ? <div className="card"><h3>Health (live)</h3><pre className="code-block">{JSON.stringify(health, null, 2)}</pre></div> : null}
      <div className="docs-nav">
        {prev ? <button className="btn btn-sm" onClick={() => nav(prev === 'overview' ? '/docs' : `/docs/${prev}`)}>← {prev}</button> : <span />}
        {next ? <button className="btn btn-sm" onClick={() => nav(`/docs/${next}`)}>{next} →</button> : <span />}
      </div>
    </div>
  )
}
