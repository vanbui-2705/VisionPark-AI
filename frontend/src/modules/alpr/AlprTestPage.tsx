import { useState } from 'react'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Alert } from '../../components/ui/Alert.tsx'

// ALPR Test Lab — development only. Mock scenarios chọn qua header X-Mock-Scenario.
type Scenario = 'success' | 'low_confidence' | 'no_plate' | 'error'
const SCENARIOS: { value: Scenario; label: string }[] = [
  { value: 'success', label: 'success — trả kết quả confidence cao' },
  { value: 'low_confidence', label: 'low_confidence — confidence thấp' },
  { value: 'no_plate', label: 'no_plate — không có biển số' },
  { value: 'error', label: 'error — ALPR lỗi xử lý' },
]

function mockResult(s: Scenario) {
  if (s === 'success') return { ai_plate: '51H123.45', normalized_plate: '51H12345', confidence: 0.91, processing_ms: 35, model_version: 'mock-alpr@dev', bbox: { x: 30, y: 30, w: 40, h: 30 } }
  if (s === 'low_confidence') return { ai_plate: '30E-99x.88', normalized_plate: '30E99X88', confidence: 0.52, processing_ms: 42, model_version: 'mock-alpr@dev', bbox: { x: 25, y: 35, w: 50, h: 25 } }
  if (s === 'no_plate') return { ai_plate: null, normalized_plate: null, confidence: 0.12, processing_ms: 28, model_version: 'mock-alpr@dev', bbox: null }
  return null
}

export function AlprTestPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [lane, setLane] = useState('LANE_IN_01')
  const [scenario, setScenario] = useState<Scenario>('success')
  const [tab, setTab] = useState<'Visual' | 'JSON' | 'Error'>('Visual')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<ReturnType<typeof mockResult> | null>(null)
  const [copyOk, setCopyOk] = useState(false)

  const onFile = (f: File | null) => {
    setFile(f)
    if (!f) { setPreview(null); return }
    const url = URL.createObjectURL(f)
    setPreview(url)
  }

  const run = async () => {
    setLoading(true)
    setErr(null)
    setResult(null)
    await new Promise((r) => setTimeout(r, 600))
    if (scenario === 'error') {
      setErr('ALPR processing error (X-Mock-Scenario: error) — development only. Raw: { code: ALPR_ERROR, message: "model failed" }')
      setTab('Error')
    } else {
      const r = mockResult(scenario)
      setResult(r)
      setTab('Visual')
      // thực thi thêm header X-Mock-Scenario khi backend thật — ở dev hiện chỉ mock client
      void fetch
    }
    setLoading(false)
  }

  const copyJson = async () => {
    if (!result) return
    await navigator.clipboard.writeText(JSON.stringify({ scenario, 'X-Mock-Scenario': scenario, result }, null, 2))
    setCopyOk(true)
    setTimeout(() => setCopyOk(false), 1200)
  }

  const clear = () => { setResult(null); setErr(null); setFile(null); setPreview(null) }

  return (
    <div>
      <Breadcrumb items={[{ label: 'ALPR', to: '/admin/alpr' }, { label: 'ALPR Test Lab' }]} />
      <h2>ALPR Test Lab</h2>
      <p className="muted">Development only — gửi header <code>X-Mock-Scenario</code> khi backend thật; ở frontend dev hiện trả mock client (có ghi chú).</p>
      <div className="card" style={{ display: 'grid', gap: 12 }}>
        <label>
          Ảnh đầu vào <input type="file" accept="image/*" aria-label="Chọn ảnh" onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
        </label>
        {preview ? <img src={preview} alt="preview" style={{ maxHeight: 240, borderRadius: 8, border: '1px solid var(--border)' }} /> : <div className="muted">Chưa chọn ảnh.</div>}
        <Select label="Lane" value={lane} onChange={(e) => setLane(e.target.value)}>
          <option value="LANE_IN_01">LANE_IN_01</option>
          <option value="LANE_OUT_01">LANE_OUT_01</option>
        </Select>
        <Select label="Mock scenario (X-Mock-Scenario)" value={scenario} onChange={(e) => setScenario(e.target.value as Scenario)}>
          {SCENARIOS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </Select>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button onClick={run} loading={loading} disabled={!file}>Chạy nhận diện</Button>
          <Button type="button" onClick={clear}>Xóa</Button>
          <Button type="button" onClick={run} disabled={loading}>Chạy lại</Button>
        </div>
        {file ? <p className="muted">{file.name} · {(file.size / 1024).toFixed(1)} KB · lane {lane}</p> : null}
      </div>

      <div className="tabs" style={{ marginTop: 16 }}>
        {(['Visual', 'JSON', 'Error'] as const).map((t) => (
          <button type="button" key={t} className={t === tab ? 'active' : undefined} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Visual' && (
        <div className="card">
          {!result ? <p className="muted">Chưa có kết quả — chọn ảnh và bấm "Chạy nhận diện".</p> : (
            <div style={{ display: 'grid', gap: 10 }}>
              {preview ? (
                <div style={{ position: 'relative', display: 'inline-block' }}>
                  <img src={preview} alt="result" style={{ maxWidth: '100%', borderRadius: 8 }} />
                  {result.bbox ? <span data-testid="bbox" style={{ position: 'absolute', left: `${result.bbox.x}%`, top: `${result.bbox.y}%`, width: `${result.bbox.w}%`, height: `${result.bbox.h}%`, border: '2px solid #22c55e', borderRadius: 4 }} /> : null}
                </div>
              ) : null}
              <ul className="kv">
                <li><b>AI plate:</b> {result.ai_plate ?? '—'}</li>
                <li><b>Normalized:</b> {result.normalized_plate ?? '—'}</li>
                <li><b>Confidence:</b> {result.confidence != null ? `${Math.round(result.confidence * 100)}%` : '—'}</li>
                <li><b>Processing:</b> {result.processing_ms} ms</li>
                <li><b>Model:</b> {result.model_version}</li>
              </ul>
              {result.confidence != null && result.confidence < 0.7 ? <Alert variant="warning">Confidence thấp — cần operator xác nhận.</Alert> : null}
              {result.ai_plate == null ? <Alert variant="warning">Không phát hiện biển số.</Alert> : null}
            </div>
          )}
        </div>
      )}

      {tab === 'JSON' && (
        <div className="card">
          <button type="button" className="btn btn-sm" onClick={copyJson} disabled={!result}>{copyOk ? '✓ Đã copy' : 'Copy JSON'}</button>
          <pre className="code-block" style={{ marginTop: 8 }}>{result ? JSON.stringify({ scenario, 'X-Mock-Scenario': scenario, result }, null, 2) : '{\n  "hint": "Chọn ảnh và chạy nhận diện để có JSON."\n}'}</pre>
        </div>
      )}

      {tab === 'Error' && (
        <div className="card">
          {err ? <Alert variant="error">{err}</Alert> : <p className="muted">Chưa có lỗi — chọn scenario "error" để xem.</p>}
        </div>
      )}
    </div>
  )
}
