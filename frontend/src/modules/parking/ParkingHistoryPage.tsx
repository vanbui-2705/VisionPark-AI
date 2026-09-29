import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { parkingTransactionsApi } from '../../api/services.ts'
import type { ParkingTransaction, ParkingHistoryFilter, TransactionStatus } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { Table } from '../../components/ui/Table.tsx'
import { ApiError } from '../../api/errors.ts'
import { recordError } from '../../lib/errorLog.ts'

const STATUS_LABEL: Record<string, string> = { PARKED: 'Đang đỗ', COMPLETED: 'Đã ra', CANCELLED: 'Đã hủy' }
const STATUS_VARIANT: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = { PARKED: 'success', COMPLETED: 'neutral', CANCELLED: 'danger' }
const SOURCE_LABEL: Record<string, string> = { STATION_AUTO: 'Tự động', OPERATOR_MANUAL: 'Thủ công' }

export function ParkingHistoryPage() {
  const [data, setData] = useState<ParkingTransaction[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [lane, setLane] = useState('ALL')
  const [status, setStatus] = useState<TransactionStatus | 'ALL'>('ALL')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const fetchData = () => {
    setLoading(true)
    setErr(null)
    parkingTransactionsApi
      .list({ limit: 200 } as ParkingHistoryFilter)
      .then((d) => setData(d))
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : 'Tải lịch sử đỗ xe thất bại.'
        setErr(msg)
        if (e instanceof ApiError) recordError({ code: e.code, status: e.status, message: e.message, source: 'parking-history', correlationId: e.correlationId })
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  const filtered = useMemo(() => {
    if (!data) return []
    return data.filter((t) => {
      if (status !== 'ALL' && t.status !== status) return false
      if (lane !== 'ALL' && t.lane_id !== lane) return false
      if (from && new Date(t.check_in_time) < new Date(from)) return false
      if (to && new Date(t.check_in_time) > new Date(to + 'T23:59:59')) return false
      if (q && !(t.license_plate ?? t.normalized_plate ?? '').toLowerCase().includes(q.toLowerCase())) return false
      return true
    })
  }, [data, q, lane, status, from, to])

  const stats = useMemo(() => {
    if (!data) return null
    return { total: data.length, parked: data.filter((x) => x.status === 'PARKED').length, manual: data.filter((x) => x.is_manual_override).length, filtered: filtered.length }
  }, [data, filtered])

  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize)
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))

  if (loading) return <Skeleton lines={8} />
  if (err) return <div><Alert variant="error">{err}</Alert><button className="btn btn-sm" onClick={fetchData} style={{ marginTop: 12 }}>Thử lại</button></div>
  if (!data || data.length === 0) return <EmptyState title="Chưa có lịch sử đỗ xe" description="Chưa có giao dịch PARKED nào." />

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Lịch sử đỗ xe' }]} />

      {/* hero header — giữ token --navy / --surface */}
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '20px 22px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Operations · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800, lineHeight: 1.2 }}>Lịch sử đỗ xe</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Theo dõi mọi lượt check-in PARKED — lọc nhanh theo biển số, làn, trạng thái, thời gian.</p>
        </div>
        {stats && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {[
              { k: 'Tổng', v: stats.total },
              { k: 'Đang đỗ', v: stats.parked, accent: '#10b981' },
              { k: 'Sửa tay', v: stats.manual, accent: '#f59e0b' },
              { k: 'Kết quả lọc', v: stats.filtered, accent: '#60a5fa' },
            ].map((s) => (
              <div key={s.k} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '10px 14px', minWidth: 92, backdropFilter: 'blur(6px)' }}>
                <div style={{ fontSize: 11, opacity: 0.75 }}>{s.k}</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: s.accent as string ?? '#fff' }}>{s.v}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* filters */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 8 }}>
          <div style={{ fontWeight: 700, fontSize: 13, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--muted)' }}>Bộ lọc</div>
          <button className="btn btn-sm btn-ghost" onClick={() => { setQ(''); setLane('ALL'); setStatus('ALL'); setFrom(''); setTo(''); setPage(0) }}>Xóa lọc</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px,1fr))', gap: 12 }}>
          <Input label="Biển số" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} placeholder="29A12345" />
          <Input label="Lane ID" value={lane === 'ALL' ? '' : lane} onChange={(e) => { setLane(e.target.value || 'ALL'); setPage(0) }} placeholder="ALL" />
          <Select label="Trạng thái" value={status} onChange={(e) => { setStatus(e.target.value as TransactionStatus | 'ALL'); setPage(0) }}>
            <option value="ALL">Tất cả</option><option value="PARKED">PARKED</option><option value="COMPLETED">COMPLETED</option><option value="CANCELLED">CANCELLED</option>
          </Select>
          <Input label="Từ ngày" type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(0) }} />
          <Input label="Đến ngày" type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(0) }} />
        </div>
      </div>

      {filtered.length === 0 ? <EmptyState title="Không có kết quả" description="Thử đổi bộ lọc hoặc xóa điều kiện tìm kiếm." /> : (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden', boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <Table>
            <thead><tr><th>Biển số</th><th>Làn</th><th>Trạng thái</th><th>Nguồn</th><th>Thời gian vào</th><th style={{ width: 90 }}></th></tr></thead>
            <tbody>
              {paged.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 800, letterSpacing: '0.06em', background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 8, padding: '4px 8px', fontSize: 13 }}>{t.license_plate}</span>
                      {t.is_manual_override ? <Badge variant="warning">sửa tay</Badge> : null}
                    </div>
                    {t.original_ai_plate && t.original_ai_plate !== t.license_plate ? <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>AI: {t.original_ai_plate}</div> : null}
                  </td>
                  <td><span style={{ fontWeight: 600 }}>{t.lane_name ?? t.lane_id}</span><div style={{ fontSize: 11, color: 'var(--muted)' }}>{t.lane_id}</div></td>
                  <td><Badge variant={STATUS_VARIANT[t.status] ?? 'neutral'}>{STATUS_LABEL[t.status] ?? t.status}</Badge></td>
                  <td><span style={{ fontSize: 13 }}>{SOURCE_LABEL[t.source] ?? t.source}</span></td>
                  <td style={{ fontSize: 13 }}>{new Date(t.check_in_time).toLocaleString('vi-VN')}</td>
                  <td><Link to={`/parking/${t.id}`} className="btn btn-sm" style={{ textDecoration: 'none', display: 'inline-block', textAlign: 'center' }}>Chi tiết</Link></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <div style={{ display: 'flex', gap: 10, padding: '12px 14px', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border)', background: '#f9fafb', flexWrap: 'wrap' }}>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>Hiển thị {paged.length} / {filtered.length} kết quả · Trang {page + 1} / {pages}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Trước</button>
              <button className="btn btn-sm btn-primary" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
