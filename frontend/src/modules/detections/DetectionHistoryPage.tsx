import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { detectionsApi } from '../../api/services.ts'
import type { Detection } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { useToast } from '../../components/ui/Toast.tsx'
import { recordError } from '../../lib/errorLog.ts'
import { ApiError } from '../../api/errors.ts'

const STATUS_LABEL: Record<string, string> = { DETECTED: 'Đã nhận diện', NEEDS_CONFIRMATION: 'Cần xác nhận', CONFIRMED: 'Đã xác nhận', CORRECTED: 'Đã sửa', NO_PLATE: 'Không có biển số', ERROR: 'Lỗi' }
const STATUS_VARIANT: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = { DETECTED: 'info', NEEDS_CONFIRMATION: 'warning', CONFIRMED: 'success', CORRECTED: 'success', NO_PLATE: 'neutral', ERROR: 'danger' }

export function DetectionHistoryPage({ admin = false }: { admin?: boolean }) {
  void admin
  const toast = useToast()
  const [items, setItems] = useState<Detection[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [err, setErr] = useState<string | null>(null)
  const [errStatus, setErrStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('ALL')
  const [lane, setLane] = useState('ALL')
  const [direction, setDirection] = useState('ALL')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const fetchData = useCallback(async () => {
    setLoading(true)
    setErr(null)
    setErrStatus(null)
    try {
      const res = await detectionsApi.list({
        q: q || undefined,
        lane_id: lane !== 'ALL' ? lane : undefined,
        status: status !== 'ALL' ? status : undefined,
        direction: direction !== 'ALL' ? direction : undefined,
        from: from || undefined,
        to: to || undefined,
        page,
        pageSize,
      })
      // client-side confidence filter not supported server-side for now; keep minimal if needed we filter locally but pagination already server-side
      setItems(res.items)
      setTotal(res.total)
      setTotalPages(res.totalPages)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Tải lịch sử thất bại.'
      setErr(msg)
      if (e instanceof ApiError) { setErrStatus(e.status); recordError({ code: e.code, status: e.status, message: e.message, source: 'detections', correlationId: e.correlationId }) }
    } finally {
      setLoading(false)
    }
  }, [q, lane, status, direction, from, to, page])

  useEffect(() => { void fetchData() }, [fetchData])

  const onFilterChange = (cb: () => void) => { cb(); setPage(0) }
  const copyId = async (id: string) => { try { await navigator.clipboard.writeText(id); toast.push('Đã copy ID', 'success') } catch { toast.push('Không copy được', 'error') } }

  if (loading) return <Skeleton lines={8} />
  if (err) {
    const msg = errStatus === 403 ? 'Bạn không có quyền xem lịch sử nhận diện.' : errStatus === 401 ? 'Vui lòng đăng nhập.' : err
    return <div><Alert variant="error">{msg}</Alert><button className="btn btn-sm" onClick={() => void fetchData()} style={{ marginTop: 12 }}>Thử lại</button></div>
  }

  return (
    <div className="data-page detections-page">
      <Breadcrumb items={[{ label: 'Lịch sử nhận diện' }]} />
      <section className="data-hero data-hero--forest detection-hero">
        <div className="data-hero-copy">
          <span className="data-kicker">Nhận diện ALPR · VisionPark</span>
          <h2>Lịch sử nhận diện</h2>
          <p>Danh sách biển số được hệ thống AI ghi nhận và xác thực.</p>
        </div>
        <div className="data-hero-stat"><strong>{total}</strong><span>tổng bản ghi</span></div>
      </section>

      <section className="data-filter-card detection-filter-card">
        <div className="detection-filter-head">
          <div><span className="data-section-kicker">BỘ LỌC DỮ LIỆU</span><h3>Thu hẹp kết quả</h3></div>
          <span className="detection-filter-hint">Tất cả bộ lọc áp dụng tức thì</span>
        </div>
        <div className="data-filter-grid">
          <Input label="Biển số" value={q} onChange={(e) => onFilterChange(() => setQ(e.target.value))} placeholder="VD: 29A12345" />
          <Input label="Làn xe" value={lane === 'ALL' ? '' : lane} onChange={(e) => onFilterChange(() => setLane(e.target.value))} placeholder="Tất cả" />
          <Select label="Hướng" value={direction} onChange={(e) => onFilterChange(() => setDirection(e.target.value))}>
            <option value="ALL">Tất cả</option>
            <option value="IN">Vào</option>
            <option value="OUT">Ra</option>
          </Select>
          <Select label="Trạng thái" value={status} onChange={(e) => onFilterChange(() => setStatus(e.target.value))}>
            <option value="ALL">Tất cả</option>
            {Object.keys(STATUS_LABEL).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </Select>
          <Input label="Từ ngày" type="date" value={from} onChange={(e) => onFilterChange(() => setFrom(e.target.value))} />
          <Input label="Đến ngày" type="date" value={to} onChange={(e) => onFilterChange(() => setTo(e.target.value))} />
        </div>
      </section>

      {!items.length ? <EmptyState title="Chưa có nhận diện" description="Không có bản ghi khớp bộ lọc." /> : (
        <section className="data-table-card detection-table-card">
          <div className="data-table-head">
            <div><span className="data-section-kicker">DỮ LIỆU LIVE</span><h3>Danh sách detection</h3></div>
            <span className="data-table-meta">{total} bản ghi · trang {page + 1}/{totalPages}</span>
          </div>
          <div className="table-wrap data-table-wrap">
            <table className="table data-table detection-table">
              <thead><tr><th>Thời gian</th><th>Làn xe</th><th>Hướng</th><th>Ảnh chụp</th><th>Biển số AI</th><th>Biển số chốt</th><th>Độ tin cậy</th><th>Trạng thái</th><th>Mã ID</th><th></th></tr></thead>
              <tbody>{items.map((d) => (
                <tr key={d.id}>
                  <td className="data-time">{new Date(d.created_at).toLocaleString('vi-VN')}</td>
                  <td className="data-lane">{d.lane_name ?? d.lane_id}</td>
                  <td>{d.direction === 'IN' ? 'Vào' : d.direction === 'OUT' ? 'Ra' : '—'}</td>
                  <td>{d.image_url ? <img className="data-thumb" src={d.image_url} alt="" /> : '—'}</td>
                  <td className="data-mono">{d.ai_plate ?? '—'}</td>
                  <td><span className="data-plate">{d.final_plate ?? d.normalized_plate ?? '—'}</span></td>
                  <td>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</td>
                  <td><span className={`detection-status detection-status--${STATUS_VARIANT[d.status] ?? 'neutral'}`}><span className="detection-status-dot" />{STATUS_LABEL[d.status] ?? d.status}</span></td>
                  <td><button type="button" className="data-id-button btn btn-ghost btn-sm" onClick={() => copyId(d.id)}>{d.id.slice(0, 8)}… ⧉</button></td>
                  <td><Link to={`/detections/${d.id}`} className="btn btn-sm">Chi tiết</Link></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div className="data-pager">
            <div>{total} bản ghi · trang {page + 1}/{totalPages}</div>
            <div className="data-pager-actions"><button type="button" className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Trước</button><button type="button" className="btn btn-sm btn-primary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>Sau →</button></div>
          </div>
        </section>
      )}
    </div>
  )
}
