import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { parkingTransactionsApi } from '../../api/services.ts'
import type { ParkingTransaction, TransactionStatus } from '../../api/domain.ts'
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
  const [items, setItems] = useState<ParkingTransaction[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [err, setErr] = useState<string | null>(null)
  const [errStatus, setErrStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [lane, setLane] = useState('ALL')
  const [status, setStatus] = useState<TransactionStatus | 'ALL'>('ALL')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const fetchData = useCallback(async () => {
    setLoading(true)
    setErr(null)
    setErrStatus(null)
    try {
      const res = await parkingTransactionsApi.list({
        q: q || undefined,
        lane_id: lane !== 'ALL' ? lane : undefined,
        status: status !== 'ALL' ? status : undefined,
        from: from || undefined,
        to: to || undefined,
        page,
        pageSize,
      })
      setItems(res.items)
      setTotal(res.total)
      setTotalPages(res.totalPages)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Tải lịch sử đỗ xe thất bại.'
      setErr(msg)
      if (e instanceof ApiError) {
        setErrStatus(e.status)
        recordError({ code: e.code, status: e.status, message: e.message, source: 'parking-history', correlationId: e.correlationId })
      }
    } finally {
      setLoading(false)
    }
  }, [q, lane, status, from, to, page])

  useEffect(() => { void fetchData() }, [fetchData])

  // reset page when filters change
  const onFilterChange = (cb: () => void) => { cb(); setPage(0) }

  if (loading) return <Skeleton lines={8} />
  if (err) {
    const isNotFound = errStatus === 404
    const isForbidden = errStatus === 403
    return <div><Alert variant="error">{isNotFound ? 'Không tìm thấy dữ liệu.' : isForbidden ? 'Bạn không có quyền xem lịch sử đỗ xe.' : err}</Alert><button className="btn btn-sm" onClick={() => void fetchData()} style={{ marginTop: 12 }}>Thử lại</button></div>
  }

  const emptyAll = total === 0 && !q && lane === 'ALL' && status === 'ALL' && !from && !to
  if (emptyAll && items.length === 0) return <EmptyState title="Chưa có lịch sử đỗ xe" description="Chưa có giao dịch PARKED nào." />

  return (
    <div className="data-page parking-page">
      <Breadcrumb items={[{ label: 'Lịch sử đỗ xe' }]} />
      <section className="data-hero data-hero--forest parking-hero">
        <div>
          <span className="data-kicker">Vận hành · VisionPark</span>
          <h2>Lịch sử đỗ xe</h2>
          <p>Theo dõi mọi lượt gửi xe — lọc nhanh theo biển số, làn xe, trạng thái và mốc thời gian.</p>
        </div>
        <div className="parking-hero-stats">
          <div className="parking-hero-stat"><div>Tổng</div><div>{total}</div></div>
        </div>
      </section>

      <section className="data-filter-card parking-filter-card">
        <div className="parking-filter-head">
          <div className="data-section-kicker">Bộ lọc vận hành</div>
          <button className="btn btn-sm btn-ghost" onClick={() => { setQ(''); setLane('ALL'); setStatus('ALL'); setFrom(''); setTo(''); setPage(0) }}>Xóa lọc</button>
        </div>
        <div className="data-filter-grid parking-filter-grid">
          <Input label="Biển số" value={q} onChange={(e) => onFilterChange(() => setQ(e.target.value))} placeholder="29A12345" />
          <Input label="Mã làn xe" value={lane === 'ALL' ? '' : lane} onChange={(e) => onFilterChange(() => setLane(e.target.value || 'ALL'))} placeholder="Tất cả làn" />
          <Select label="Trạng thái" value={status} onChange={(e) => onFilterChange(() => setStatus(e.target.value as TransactionStatus | 'ALL'))}>
            <option value="ALL">Tất cả</option>
            <option value="PARKED">Đang đỗ</option>
            <option value="COMPLETED">Đã ra</option>
            <option value="CANCELLED">Đã hủy</option>
          </Select>
          <Input label="Từ ngày" type="date" value={from} onChange={(e) => onFilterChange(() => setFrom(e.target.value))} />
          <Input label="Đến ngày" type="date" value={to} onChange={(e) => onFilterChange(() => setTo(e.target.value))} />
        </div>
      </section>

      {items.length === 0 ? <EmptyState title="Không có kết quả" description="Thử đổi bộ lọc hoặc xóa điều kiện tìm kiếm." /> : (
        <section className="data-table-card parking-table-card">
          <Table>
            <thead><tr><th>Biển số</th><th>Làn</th><th>Trạng thái</th><th>Nguồn</th><th>Thời gian vào</th><th className="parking-action-col"></th></tr></thead>
            <tbody>
              {items.map((t) => (
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
            <div>Hiển thị <strong>{items.length}</strong> / {total} kết quả <span className="parking-pager-separator">·</span> Trang {page + 1} / {totalPages}</div>
            <div className="data-pager-actions">
              <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Trước</button>
              <button className="btn btn-sm btn-primary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>Sau</button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
