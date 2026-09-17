import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { detectionsApi } from '../../api/services.ts'
import type { Detection } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Table } from '../../components/ui/Table.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { useToast } from '../../components/ui/Toast.tsx'
import { recordError } from '../../lib/errorLog.ts'
import { ApiError } from '../../api/errors.ts'

const STATUS_LABEL: Record<string, string> = {
  DETECTED: 'Detected',
  NEEDS_CONFIRMATION: 'Needs confirmation',
  CONFIRMED: 'Confirmed',
  CORRECTED: 'Corrected',
  NO_PLATE: 'No plate',
  ERROR: 'Error',
}

const STATUS_VARIANT: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  DETECTED: 'info',
  NEEDS_CONFIRMATION: 'warning',
  CONFIRMED: 'success',
  CORRECTED: 'success',
  NO_PLATE: 'neutral',
  ERROR: 'danger',
}

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
    detectionsApi
      .list({ limit: 200 })
      .then((d) => { if (alive) setData(d) })
      .catch((e: unknown) => {
        if (!alive) return
        const msg = e instanceof Error ? e.message : 'Tải lịch sử thất bại.'
        setErr(msg)
        if (e instanceof ApiError) recordError({ code: e.code, status: e.status, message: e.message, source: 'detections', correlationId: e.correlationId })
      })
      .finally(() => { if (alive) setLoading(false) })
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

  const copyId = async (id: string) => {
    try { await navigator.clipboard.writeText(id); toast.push('Đã copy ID', 'success') } catch { toast.push('Không copy được', 'error') }
  }

  if (loading) return <Skeleton lines={8} />
  if (err) return <Alert variant="error">{err}</Alert>

  return (
    <div>
      <Breadcrumb items={[{ label: 'Lịch sử nhận diện' }]} />
      <div className="page-head"><h2>Lịch sử nhận diện</h2><p className="muted">API hiện chỉ hỗ trợ lane_id + limit — các filter khác là client-side.</p></div>
      <div className="filters">
        <Input label="Biển số" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} placeholder="29A12345" />
        <Select label="Lane" value={lane} onChange={(e) => { setLane(e.target.value); setPage(0) }}>
          <option value="ALL">ALL</option>
          {(data ?? []).length ? [...new Set((data ?? []).map((d) => d.lane_id))].map((id) => <option key={id} value={id}>{id}</option>) : null}
        </Select>
        <Select label="Hướng" value={direction} onChange={(e) => { setDirection(e.target.value); setPage(0) }}>
          <option value="ALL">ALL</option><option value="IN">IN</option><option value="OUT">OUT</option>
        </Select>
        <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(0) }}>
          <option value="ALL">ALL</option>
          {Object.keys(STATUS_LABEL).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </Select>
        <Input label="Confidence ≥ (%)" value={minConf} onChange={(e) => setMinConf(e.target.value)} placeholder="0" />
        <Input label="Confidence ≤ (%)" value={maxConf} onChange={(e) => setMaxConf(e.target.value)} placeholder="100" />
        <Input label="Từ ngày" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <Input label="Đến ngày" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </div>
      {!filtered.length ? (
        <EmptyState title="Chưa có nhận diện" description="Không có bản ghi khớp bộ lọc." />
      ) : (
        <>
          <Table>
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Lane</th>
                <th>Hướng</th>
                <th>Ảnh</th>
                <th>AI Plate</th>
                <th>Final Plate</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>ID</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((d) => (
                <tr key={d.id}>
                  <td>{new Date(d.created_at).toLocaleString('vi-VN')}</td>
                  <td>{d.lane_name ?? d.lane_id}</td>
                  <td>{d.direction ?? '—'}</td>
                  <td>{d.image_url ? <img src={d.image_url} alt="" style={{ height: 36, borderRadius: 4 }} /> : '—'}</td>
                  <td>{d.ai_plate ?? '—'}</td>
                  <td>{d.final_plate ?? d.normalized_plate ?? '—'}</td>
                  <td>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</td>
                  <td><Badge variant={STATUS_VARIANT[d.status] ?? 'neutral'}>{STATUS_LABEL[d.status] ?? d.status}</Badge></td>
                  <td><button type="button" className="btn btn-ghost btn-sm" onClick={() => copyId(d.id)}>{d.id.slice(0, 8)}… ⧉</button></td>
                  <td><Link to={`/detections/${d.id}`}>Chi tiết</Link></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <div className="pager">
            <span className="muted">{filtered.length} bản ghi · trang {page + 1}/{pages}</span>
            <button type="button" className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Trước</button>
            <button type="button" className="btn btn-sm" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>Sau →</button>
          </div>
        </>
      )}
    </div>
  )
}
