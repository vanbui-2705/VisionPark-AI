import { useEffect, useState } from 'react'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Drawer } from '../../components/ui/Drawer.tsx'
import { getErrorLog, clearErrorLog, subscribeErrorLog, type ClientError } from '../../lib/errorLog.ts'

export function ErrorCenterPage() {
  const [rows, setRows] = useState<ClientError[]>(getErrorLog())
  const [selected, setSelected] = useState<ClientError | null>(null)
  useEffect(() => subscribeErrorLog(() => setRows([...getErrorLog()])), [])

  return (
    <div className="data-page errors-page">
      <Breadcrumb items={[{ label: 'Trung tâm lỗi' }]} />

      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">CHẨN ĐOÁN SỰ CỐ · VISIONPARK</span>
          <h2>Trung tâm lỗi</h2>
          <p>Theo dõi sự cố kết nối và lỗi phản hồi API để hỗ trợ kỹ thuật kịp thời.</p>
        </div>
        <div className="data-hero-stat"><strong>{rows.length}</strong><span>bản ghi cục bộ</span></div>
      </section>

      <div className="errors-toolbar">
        <button type="button" className="btn btn-sm" onClick={() => { clearErrorLog(); setSelected(null) }}>Xóa nhật ký</button>
        <span className="muted" style={{ fontSize: 12 }}>{rows.length} bản ghi lỗi cục bộ</span>
      </div>

      {rows.length === 0 ? (
        <div className="data-table-card errors-empty"><div className="errors-empty-title">Không có sự cố</div><p className="muted">Hệ thống hoạt động bình thường, chưa ghi nhận lỗi.</p></div>
      ) : (
        <section className="data-table-card">
          <div className="data-table-head"><div><span className="data-section-kicker">CLIENT DIAGNOSTICS</span><h3>Nhật ký lỗi</h3></div><span className="data-table-meta">{rows.length} bản ghi</span></div>
          <div className="table-wrap data-table-wrap">
            <table className="table data-table errors-table">
              <thead><tr><th>Thời gian</th><th>Mã lỗi</th><th>Trạng thái</th><th>Nội dung</th><th>Nguồn</th><th>Mã đối soát</th><th></th></tr></thead>
              <tbody>{rows.map((e) => (
                <tr key={e.id}>
                  <td className="data-time">{new Date(e.time).toLocaleString('vi-VN')}</td>
                  <td><code>{e.code}</code></td>
                  <td>{String(e.status)}</td>
                  <td className="error-message">{e.message}</td>
                  <td>{e.source}</td>
                  <td>{e.correlationId ? <code>{e.correlationId.slice(0, 12)}…</code> : '—'}</td>
                  <td><button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelected(e)}>Chi tiết</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}

      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected ? `Chi tiết lỗi #${selected.id}` : ''}>
        {selected ? (
          <div className="error-detail-grid">
            <div><b>Mã lỗi:</b> {selected.code}</div>
            <div><b>Mã HTTP:</b> {selected.status}</div>
            <div><b>Nội dung:</b> {selected.message}</div>
            <div><b>Nguồn phát sinh:</b> {selected.source}</div>
            <div><b>Thời gian:</b> {new Date(selected.time).toLocaleString('vi-VN')}</div>
            <div><b>Mã đối soát:</b> {selected.correlationId ?? '—'}</div>
            {selected.correlationId ? <div className="muted">Gửi mã đối soát này cho bộ phận kỹ thuật để tra cứu log trên server.</div> : null}
            <pre className="code-block">{JSON.stringify(selected, null, 2)}</pre>
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}
