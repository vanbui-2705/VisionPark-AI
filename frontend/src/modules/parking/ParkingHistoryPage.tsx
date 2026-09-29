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

const STATUS_LABEL: Record<string, string> = {
  PARKED: 'Đang đỗ',
  COMPLETED: 'Đã ra',
  CANCELLED: 'Đã hủy',
}

const STATUS_VARIANT: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  PARKED: 'success',
  COMPLETED: 'neutral',
  CANCELLED: 'danger',
}

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
    const params: ParkingHistoryFilter = { limit: 200 }
    parkingTransactionsApi
      .list(params)
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

  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize)
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))

  if (loading) return <Skeleton lines={8} />
  if (err) return <div><Alert variant="error">{err}</Alert><button className="btn btn-sm" onClick={fetchData} style={{ marginTop: 8 }}>Thử lại</button></div>
  if (!data || data.length === 0) return <EmptyState title="Chưa có lịch sử đỗ xe" description="Chưa có giao dịch PARKED nào." />

  return (
    <div>
      <Breadcrumb items={[{ label: 'Lịch sử đỗ xe' }]} />
      <div className="page-head"><h2>Lịch sử đỗ xe</h2><p className="muted">Phase 2 — Filter: biển số, làn, trạng thái, khoảng thời gian. Duy Anh.</p></div>
      <div className="filters" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <Input label="Biển số" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} placeholder="29A12345" />
        <Input label="Lane ID" value={lane === 'ALL' ? '' : lane} onChange={(e) => { setLane(e.target.value || 'ALL'); setPage(0) }} placeholder="ALL" />
        <Select label="Trạng thái" value={status} onChange={(e) => { setStatus(e.target.value as TransactionStatus | 'ALL'); setPage(0) }}>
          <option value="ALL">Tất cả</option>
          <option value="PARKED">PARKED</option>
          <option value="COMPLETED">COMPLETED</option>
          <option value="CANCELLED">CANCELLED</option>
        </Select>
        <Input label="Từ ngày" type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(0) }} />
        <Input label="Đến ngày" type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(0) }} />
      </div>
      {filtered.length === 0 ? <EmptyState title="Không có kết quả" description="Thử đổi bộ lọc." /> : (
        <>
          <Table>
            <thead><tr><th>Biển số</th><th>Làn</th><th>Trạng thái</th><th>Nguồn</th><th>Thời gian vào</th><th></th></tr></thead>
            <tbody>
              {paged.map((t) => (
                <tr key={t.id}>
                  <td><strong>{t.license_plate}</strong>{t.is_manual_override ? <Badge variant="warning">sửa tay</Badge> : null}</td>
                  <td>{t.lane_name ?? t.lane_id}</td>
                  <td><Badge variant={STATUS_VARIANT[t.status] ?? 'neutral'}>{STATUS_LABEL[t.status] ?? t.status}</Badge></td>
                  <td>{t.source}</td>
                  <td>{new Date(t.check_in_time).toLocaleString('vi-VN')}</td>
                  <td><Link to={`/parking/${t.id}`}>Chi tiết</Link></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
            <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Trước</button>
            <span className="muted">Trang {page + 1} / {pages}</span>
            <button className="btn btn-sm" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
          </div>
        </>
      )}
    </div>
  )
}
