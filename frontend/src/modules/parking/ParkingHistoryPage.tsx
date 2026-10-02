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
    <div className="data-page parking-page">
      <Breadcrumb items={[{ label: 'Lịch sử đỗ xe' }]} />

      {/* hero header — giữ token --navy / --surface */}
      <section className="data-hero data-hero--forest parking-hero">
        <div>
          <span className="data-kicker">Vận hành · VisionPark</span>
          <h2>Lịch sử đỗ xe</h2>
          <p>Theo dõi mọi lượt gửi xe — lọc nhanh theo biển số, làn xe, trạng thái và mốc thời gian.</p>
        </div>
        {stats && (
          <div className="parking-hero-stats">
            {[
              { k: 'Tổng', v: stats.total },
              { k: 'Đang đỗ', v: stats.parked },
              { k: 'Sửa tay', v: stats.manual },
              { k: 'Kết quả lọc', v: stats.filtered },
            ].map((s) => (
              <div key={s.k} className="parking-hero-stat">
                <div>{s.k}</div>
                <div>{s.v}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* filters */}
      <section className="data-filter-card parking-filter-card">
        <div className="parking-filter-head">
          <div className="data-section-kicker">Bộ lọc vận hành</div>
          <button className="btn btn-sm btn-ghost" onClick={() => { setQ(''); setLane('ALL'); setStatus('ALL'); setFrom(''); setTo(''); setPage(0) }}>Xóa lọc</button>
        </div>
        <div className="data-filter-grid parking-filter-grid">
          <Input label="Biển số" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} placeholder="29A12345" />
          <Input label="Mã làn xe" value={lane === 'ALL' ? '' : lane} onChange={(e) => { setLane(e.target.value || 'ALL'); setPage(0) }} placeholder="Tất cả làn" />
          <Select label="Trạng thái" value={status} onChange={(e) => { setStatus(e.target.value as TransactionStatus | 'ALL'); setPage(0) }}>
            <option value="ALL">Tất cả</option>
            <option value="PARKED">Đang đỗ</option>
            <option value="COMPLETED">Đã ra</option>
            <option value="CANCELLED">Đã hủy</option>
          </Select>
          <Input label="Từ ngày" type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(0) }} />
          <Input label="Đến ngày" type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(0) }} />
        </div>
      </section>

      {filtered.length === 0 ? <EmptyState title="Không có kết quả" description="Thử đổi bộ lọc hoặc xóa điều kiện tìm kiếm." /> : (
        <section className="data-table-card parking-table-card">
          <Table>
            <thead><tr><th>Biển số</th><th>Làn</th><th>Trạng thái</th><th>Nguồn</th><th>Thời gian vào</th><th className="parking-action-col"></th></tr></thead>
            <tbody>
              {paged.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div className="parking-plate-line">
                      <span className="parking-plate">{t.license_plate}</span>
                      {t.is_manual_override ? <span className="parking-manual-mark"><span aria-hidden="true">↗</span> Sửa tay</span> : null}
                    </div>
                    {t.original_ai_plate && t.original_ai_plate !== t.license_plate ? <div className="parking-ai-plate">AI nhận diện: {t.original_ai_plate}</div> : null}
                  </td>
                  <td><strong className="parking-lane-name">{t.lane_name ?? t.lane_id}</strong><span className="parking-lane-id">{t.lane_id}</span></td>
                  <td><Badge variant={STATUS_VARIANT[t.status] ?? 'neutral'}>{STATUS_LABEL[t.status] ?? t.status}</Badge></td>
                  <td><span className={`parking-source parking-source--${t.source === 'OPERATOR_MANUAL' ? 'manual' : 'auto'}`}><span aria-hidden="true">{t.source === 'OPERATOR_MANUAL' ? '✎' : '●'}</span>{SOURCE_LABEL[t.source] ?? t.source}</span></td>
                  <td className="parking-time">{new Date(t.check_in_time).toLocaleString('vi-VN')}</td>
                  <td><Link to={`/parking/${t.id}`} className="btn btn-sm parking-detail-link">Xem chi tiết <span aria-hidden="true">→</span></Link></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <div className="data-pager parking-pager">
            <div>Hiển thị <strong>{paged.length}</strong> / {filtered.length} kết quả <span className="parking-pager-separator">·</span> Trang {page + 1} / {pages}</div>
            <div className="data-pager-actions">
              <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Trước</button>
              <button className="btn btn-sm btn-primary" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>Sau</button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
