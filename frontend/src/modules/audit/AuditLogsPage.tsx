import { useCallback, useEffect, useState } from 'react'
import { auditApi } from '../../api/services.ts'
import type { AuditLog } from '../../api/domain.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { ApiError } from '../../api/errors.ts'

function sanitize(obj: unknown): unknown {
  if (!obj || typeof obj !== 'object') return obj
  const o = obj as Record<string, unknown>
  const out: Record<string, unknown> = { ...o }
  for (const k of ['password', 'password_hash', 'hash', 'jwt', 'access_token', 'secret', 'token']) if (k in out) out[k] = '[REDACTED]'
  return out
}

export function AuditLogsPage() {
  const [items, setItems] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [err, setErr] = useState<string | null>(null)
  const [errStatus, setErrStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [actor, setActor] = useState('')
  const [action, setAction] = useState('')
  const [resource, setResource] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const fetchData = useCallback(async () => {
    setLoading(true)
    setErr(null)
    setErrStatus(null)
    try {
      const res = await auditApi.list({
        actor: actor || undefined,
        action: action || undefined,
        resource: resource || undefined,
        from: from || undefined,
        to: to || undefined,
        q: q || undefined,
        page,
        pageSize,
      })
      setItems(res.items)
      setTotal(res.total)
      setTotalPages(res.totalPages)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Không tải được audit logs')
      if (e instanceof ApiError) setErrStatus(e.status)
    } finally {
      setLoading(false)
    }
  }, [actor, action, resource, from, to, q, page])

  useEffect(() => { void fetchData() }, [fetchData])

  const onFilterChange = (cb: () => void) => { cb(); setPage(0) }

  if (loading) return <Spinner />
  if (err) {
    const msg = errStatus === 403 ? 'Bạn không có quyền xem audit logs.' : errStatus === 401 ? 'Vui lòng đăng nhập lại.' : err
    return <div><Alert variant="error">{msg}</Alert><button className="btn btn-sm" onClick={() => void fetchData()} style={{ marginTop: 12 }}>Thử lại</button></div>
  }

  const hasActiveFilter = !!(actor || action || resource || from || to || q)

  return (
    <div className="data-page audit-page">
      <section className="data-hero data-hero--cream">
        <div className="data-hero-copy">
          <span className="data-kicker">NHẬT KÝ HỆ THỐNG · VISIONPARK</span>
          <h2>Nhật ký kiểm tra</h2>
          <p>Theo dõi người thực hiện, hành động, tài nguyên và mã tương quan. Dữ liệu nhạy cảm được ẩn khi hiển thị.</p>
        </div>
        <div className="data-hero-stat"><strong>{total}</strong><span>bản ghi</span></div>
      </section>

      <section className="data-filter-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span className="data-section-kicker">Bộ lọc audit</span>
          <button className="btn btn-sm btn-ghost" onClick={() => { setActor(''); setAction(''); setResource(''); setFrom(''); setTo(''); setQ(''); setPage(0) }}>Xóa lọc</button>
        </div>
        <div className="data-filter-grid">
          <Input label="Actor" value={actor} onChange={(e) => onFilterChange(() => setActor(e.target.value))} placeholder="Tên người thực hiện" />
          <Select label="Action" value={action} onChange={(e) => onFilterChange(() => setAction(e.target.value))}>
            <option value="">Tất cả</option>
            <option value="LANE_CREATE">LANE_CREATE</option>
            <option value="CHECK_IN">CHECK_IN</option>
            <option value="CONFIRM_PLATE">CONFIRM_PLATE</option>
          </Select>
          <Select label="Resource" value={resource} onChange={(e) => onFilterChange(() => setResource(e.target.value))}>
            <option value="">Tất cả</option>
            <option value="Lane">Lane</option>
            <option value="Detection">Detection</option>
            <option value="ParkingTransaction">ParkingTransaction</option>
          </Select>
          <Input label="Từ ngày" type="date" value={from} onChange={(e) => onFilterChange(() => setFrom(e.target.value))} />
          <Input label="Đến ngày" type="date" value={to} onChange={(e) => onFilterChange(() => setTo(e.target.value))} />
          <Input label="Tìm kiếm" value={q} onChange={(e) => onFilterChange(() => setQ(e.target.value))} placeholder="keyword" />
        </div>
      </section>

      {items.length === 0 ? (
        hasActiveFilter ? <EmptyState title="Không có kết quả" description="Thử đổi bộ lọc hoặc xóa điều kiện tìm kiếm." /> : <EmptyState title="Chưa có nhật ký kiểm tra" />
      ) : <>
      <section className="data-table-card">
        <div className="data-table-head">
          <div><span className="data-section-kicker">LỊCH SỬ THAO TÁC</span><h3>Hoạt động quản trị</h3></div>
          <span className="data-table-meta">{total} bản ghi · trang {page + 1}/{totalPages}</span>
        </div>
        <div className="table-wrap data-table-wrap">
          <table className="table data-table audit-table">
            <thead><tr><th>Thời gian</th><th>Người thực hiện</th><th>Hành động</th><th>Tài nguyên</th><th>Mã tài nguyên</th><th>Mã tương quan</th><th></th></tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.id}>
                <td className="data-time">{new Date(r.time).toLocaleString('vi-VN')}</td>
                <td><strong>{r.actor}</strong></td><td><Badge>{r.action}</Badge></td><td>{r.resource}</td><td className="data-mono">{r.resource_id}</td><td className="data-mono">{r.correlation_id ?? '—'}</td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>{expanded === r.id ? 'Thu gọn' : 'Chi tiết'}</button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div className="data-pager">
          <div>{total} bản ghi · trang {page + 1}/{totalPages}</div>
          <div className="data-pager-actions">
            <button type="button" className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Trước</button>
            <button type="button" className="btn btn-sm btn-primary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>Sau</button>
          </div>
        </div>
      </section>
      {expanded ? (() => { const row = items.find((x) => x.id === expanded); if (!row) return null; const _after = row.after && typeof row.after === 'object' ? row.after as Record<string, unknown> : null; return (
        <section className="data-table-card audit-detail">
          <div className="data-table-head"><div><span className="data-section-kicker">BẢN GHI {row.id}</span><h3>Chi tiết nhật ký</h3></div></div>
          {_after ? <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12, fontSize: 13 }}><span>{_after.ai_plate ? String(_after.ai_plate) : '—'}</span><span>{_after.final_plate ? String(_after.final_plate) : String((_after as Record<string,unknown>).plate ?? '—')}</span><span>{String(_after.source ?? row.source ?? '—')}</span><span>{row.actor ?? '—'}</span></div> : null}
          <div className="audit-detail-grid">
            <div><div className="data-section-kicker">TRƯỚC</div><pre className="code-block">{JSON.stringify(sanitize(row.before), null, 2) ?? '—'}</pre></div>
            <div><div className="data-section-kicker">SAU</div><pre className="code-block">{JSON.stringify(sanitize(row.after), null, 2) ?? '—'}</pre></div>
          </div>
        </section>
      ) })() : null}
      </>}
    </div>
  )
}
