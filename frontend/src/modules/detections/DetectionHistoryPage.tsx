import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { detectionsApi } from '../../api/services.ts'
import type { Detection } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { useToast } from '../../components/ui/Toast.tsx'
import { recordError } from '../../lib/errorLog.ts'
import { ApiError } from '../../api/errors.ts'

const STATUS_LABEL: Record<string, string> = { DETECTED: 'Detected', NEEDS_CONFIRMATION: 'Needs confirmation', CONFIRMED: 'Confirmed', CORRECTED: 'Corrected', NO_PLATE: 'No plate', ERROR: 'Error' }
const STATUS_VARIANT: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = { DETECTED: 'info', NEEDS_CONFIRMATION: 'warning', CONFIRMED: 'success', CORRECTED: 'success', NO_PLATE: 'neutral', ERROR: 'danger' }

export function DetectionHistoryPage({ admin = false }: { admin?: boolean }) {
  void admin
  const toast = useToast()
  const [data, setData] = useState<Detection[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('ALL')
  const [lane, setLane] = useState('ALL')
  const [direction, setDirection] = useState('ALL')
  const [minConf, setMinConf] = useState('')
  const [maxConf, setMaxConf] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  useEffect(() => {
    let alive = true
    setLoading(true)
    detectionsApi.list({ limit: 200 }).then((d) => { if (alive) setData(d) }).catch((e: unknown) => {
      if (!alive) return
      const msg = e instanceof Error ? e.message : 'Tải lịch sử thất bại.'
      setErr(msg)
      if (e instanceof ApiError) recordError({ code: e.code, status: e.status, message: e.message, source: 'detections', correlationId: e.correlationId })
    }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const filtered = useMemo(() => {
    if (!data) return []
    const min = minConf ? Number(minConf) / 100 : null
    const max = maxConf ? Number(maxConf) / 100 : null
    return data.filter((d) => {
      if (status !== 'ALL' && d.status !== status) return false
      if (lane !== 'ALL' && d.lane_id !== lane) return false
      if (direction !== 'ALL' && d.direction !== direction) return false
      if (min != null && (d.confidence ?? 0) < min) return false
      if (max != null && (d.confidence ?? 1) > max) return false
      if (from && new Date(d.created_at) < new Date(from)) return false
      if (to && new Date(d.created_at) > new Date(to + 'T23:59:59')) return false
      if (q && !(d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '').toLowerCase().includes(q.toLowerCase())) return false
      return true
    })
  }, [data, q, status, lane, direction, minConf, maxConf, from, to])

  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize)
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const copyId = async (id: string) => { try { await navigator.clipboard.writeText(id); toast.push('Đã copy ID', 'success') } catch { toast.push('Không copy được', 'error') } }

  if (loading) return <Skeleton lines={8} />
  if (err) return <Alert variant="error">{err}</Alert>

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Lịch sử nhận diện' }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>ALPR History · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Lịch sử nhận diện</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>API hiện chỉ hỗ trợ lane_id + limit — các filter khác là client-side. {data ? `${data.length} bản ghi` : ''}</p>
        </div>
        <Badge>{filtered.length} kết quả</Badge>
      </div>

      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Bộ lọc</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px,1fr))', gap: 12 }}>
          <Input label="Biển số" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} placeholder="29A12345" />
          <Select label="Lane" value={lane} onChange={(e) => { setLane(e.target.value); setPage(0) }}>
            <option value="ALL">ALL</option>
            {(data ?? []).length ? [...new Set((data ?? []).map((d) => d.lane_id))].map((id) => <option key={id} value={id}>{id}</option>) : null}
          </Select>
          <Select label="Hướng" value={direction} onChange={(e) => { setDirection(e.target.value); setPage(0) }}><option value="ALL">ALL</option><option value="IN">IN</option><option value="OUT">OUT</option></Select>
          <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(0) }}><option value="ALL">ALL</option>{Object.keys(STATUS_LABEL).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}</Select>
          <Input label="Confidence ≥ (%)" value={minConf} onChange={(e) => setMinConf(e.target.value)} placeholder="0" />
          <Input label="Confidence ≤ (%)" value={maxConf} onChange={(e) => setMaxConf(e.target.value)} placeholder="100" />
          <Input label="Từ ngày" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          <Input label="Đến ngày" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
      </section>

      {!filtered.length ? <EmptyState title="Chưa có nhận diện" description="Không có bản ghi khớp bộ lọc." /> : (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden', boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <div style={{ overflow: 'auto' }}>
            <table className="table" style={{ margin: 0 }}>
              <thead><tr><th>Thời gian</th><th>Lane</th><th>Hướng</th><th>Ảnh</th><th>AI Plate</th><th>Final Plate</th><th>Confidence</th><th>Status</th><th>ID</th><th></th></tr></thead>
              <tbody>{paged.map((d) => (
                <tr key={d.id}>
                  <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>{new Date(d.created_at).toLocaleString('vi-VN')}</td>
                  <td style={{ fontWeight: 600 }}>{d.lane_name ?? d.lane_id}</td>
                  <td>{d.direction ?? '—'}</td>
                  <td>{d.image_url ? <img src={d.image_url} alt="" style={{ height: 36, borderRadius: 8, border: '1px solid var(--border)' }} /> : '—'}</td>
                  <td style={{ fontFamily: 'ui-monospace, monospace' }}>{d.ai_plate ?? '—'}</td>
                  <td><span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 700, background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 8, padding: '3px 6px' }}>{d.final_plate ?? d.normalized_plate ?? '—'}</span></td>
                  <td>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</td>
                  <td><Badge variant={STATUS_VARIANT[d.status] ?? 'neutral'}>{STATUS_LABEL[d.status] ?? d.status}</Badge></td>
                  <td><button type="button" className="btn btn-ghost btn-sm" onClick={() => copyId(d.id)}>{d.id.slice(0, 8)}… ⧉</button></td>
                  <td><Link to={`/detections/${d.id}`} className="btn btn-sm">Chi tiết</Link></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: 10, padding: '12px 14px', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border)', background: '#f9fafb', flexWrap: 'wrap' }}>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>{filtered.length} bản ghi · trang {page + 1}/{pages}</div>
            <div style={{ display: 'flex', gap: 8 }}><button type="button" className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Trước</button><button type="button" className="btn btn-sm btn-primary" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>Sau →</button></div>
          </div>
        </div>
      )}
    </div>
  )
}
