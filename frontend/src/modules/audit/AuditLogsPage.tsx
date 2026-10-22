import { t as translate } from "../../lib/i18n"
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
      const res = await auditApi.page({
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
      setErr(e instanceof Error ? e.message : translate("Không tải được audit logs"))
      if (e instanceof ApiError) setErrStatus(e.status)
    } finally {
      setLoading(false)
    }
  }, [actor, action, resource, from, to, q, page])

  useEffect(() => { void fetchData() }, [fetchData])

  const onFilterChange = (cb: () => void) => { cb(); setPage(0) }

  if (loading) return <Spinner />
  if (err) {
    const msg = errStatus === 403 ? translate("Bạn không có quyền xem audit logs.") : errStatus === 401 ? translate("Vui lòng đăng nhập lại.") : err
    return <div><Alert variant="error">{msg}</Alert><button className="btn btn-sm" onClick={() => void fetchData()} style={{ marginTop: 12 }}>{translate("Thử lại")}</button></div>
  }

  const hasActiveFilter = !!(actor || action || resource || from || to || q)

  return (
    <div className="data-page audit-page">
      <section className="data-hero data-hero--cream">
        <div className="data-hero-copy">
          <span className="data-kicker">{translate("NHẬT KÝ HỆ THỐNG · VISIONPARK")}</span>
          <h2>{translate("Nhật ký kiểm tra")}</h2>
          <p>{translate("Theo dõi người thực hiện, hành động, tài nguyên và mã tương quan. Dữ liệu nhạy cảm được ẩn khi hiển thị.")}</p>
        </div>
        <div className="data-hero-stat"><strong>{total}</strong><span>{translate("bản ghi")}</span></div>
      </section>

      <section className="data-filter-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span className="data-section-kicker">{translate("Bộ lọc audit")}</span>
          <button className="btn btn-sm btn-ghost" onClick={() => { setActor(''); setAction(''); setResource(''); setFrom(''); setTo(''); setQ(''); setPage(0) }}>{translate("Xóa lọc")}</button>
        </div>
        <div className="data-filter-grid">
          <Input label="Actor" value={actor} onChange={(e) => onFilterChange(() => setActor(e.target.value))} placeholder={translate("Tên người thực hiện")} />
          <Select label="Action" value={action} onChange={(e) => onFilterChange(() => setAction(e.target.value))}>
            <option value="">{translate("Tất cả")}</option>
            <option value="LANE_CREATE">LANE_CREATE</option>
            <option value="CHECK_IN">CHECK_IN</option>
            <option value="CONFIRM_PLATE">CONFIRM_PLATE</option>
          </Select>
          <Select label="Resource" value={resource} onChange={(e) => onFilterChange(() => setResource(e.target.value))}>
            <option value="">{translate("Tất cả")}</option>
            <option value="Lane">Lane</option>
            <option value="Detection">Detection</option>
            <option value="ParkingTransaction">ParkingTransaction</option>
          </Select>
          <Input label={translate("Từ ngày")} type="date" value={from} onChange={(e) => onFilterChange(() => setFrom(e.target.value))} />
          <Input label={translate("Đến ngày")} type="date" value={to} onChange={(e) => onFilterChange(() => setTo(e.target.value))} />
          <Input label={translate("Tìm kiếm")} value={q} onChange={(e) => onFilterChange(() => setQ(e.target.value))} placeholder="keyword" />
        </div>
      </section>

      {items.length === 0 ? (
        hasActiveFilter ? <EmptyState title={translate("Không có kết quả")} description={translate("Thử đổi bộ lọc hoặc xóa điều kiện tìm kiếm.")} /> : <EmptyState title={translate("Chưa có nhật ký kiểm tra")} />
      ) : <>
      <section className="data-table-card">
        <div className="data-table-head">
          <div><span className="data-section-kicker">{translate("LỊCH SỬ THAO TÁC")}</span><h3>{translate("Hoạt động quản trị")}</h3></div>
          <span className="data-table-meta">{total}{translate("bản ghi · trang")}{page + 1}/{totalPages}</span>
        </div>
        <div className="table-wrap data-table-wrap">
          <table className="table data-table audit-table">
            <thead><tr><th>{translate("Thời gian")}</th><th>{translate("Người thực hiện")}</th><th>{translate("Hành động")}</th><th>{translate("Tài nguyên")}</th><th>{translate("Mã tài nguyên")}</th><th>{translate("Mã tương quan")}</th><th></th></tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.id}>
                <td className="data-time">{new Date(r.time).toLocaleString('vi-VN')}</td>
                <td><strong>{r.actor}</strong></td><td><Badge>{r.action}</Badge></td><td>{r.resource}</td><td className="data-mono">{r.resource_id}</td><td className="data-mono">{r.correlation_id ?? '—'}</td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>{expanded === r.id ? translate("Thu gọn") : translate("Chi tiết")}</button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div className="data-pager">
          <div>{total}{translate("bản ghi · trang")}{page + 1}/{totalPages}</div>
          <div className="data-pager-actions">
            <button type="button" className="btn btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>{translate("Trước")}</button>
            <button type="button" className="btn btn-sm btn-primary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>Sau</button>
          </div>
        </div>
      </section>
      {expanded ? (() => { const row = items.find((x) => x.id === expanded); if (!row) return null; const after = row.after && typeof row.after === 'object' ? row.after as Record<string, unknown> : null; return (
        <section className="data-table-card audit-detail">
          <div className="data-table-head"><div><span className="data-section-kicker">{translate("BẢN GHI")} {row.id}</span><h3>{translate("Chi tiết nhật ký")}</h3></div></div>
          <div className="audit-detail-grid">
            <div>AI plate: <span>{String(after?.ai_plate ?? '—')}</span></div>
            <div>Final plate: <span>{String(after?.final_plate ?? '—')}</span></div>
            <div>Actor: {row.actor ?? '—'}</div>
            <div>Source: <span>{String(after?.source ?? row.source ?? '—')}</span></div>
            <div>Timestamp: {new Date(row.time).toLocaleString('vi-VN')}</div>
          </div>
          <div className="data-table-head"><div><span className="data-section-kicker">{translate("BẢN GHI")}{row.id}</span><h3>{translate("Chi tiết nhật ký")}</h3></div></div>
          <div className="audit-detail-grid">
            <div><div className="data-section-kicker">{translate("TRƯỚC")}</div><pre className="code-block">{JSON.stringify(sanitize(row.before), null, 2) ?? '—'}</pre></div>
            <div><div className="data-section-kicker">SAU</div><pre className="code-block">{JSON.stringify(sanitize(row.after), null, 2) ?? '—'}</pre></div>
          </div>
        </section>
      ) })() : null}
      </>}
    </div>
  )
}
