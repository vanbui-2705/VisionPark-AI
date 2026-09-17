import { useEffect, useState } from 'react'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Drawer } from '../../components/ui/Drawer.tsx'
import { getErrorLog, clearErrorLog, subscribeErrorLog, type ClientError } from '../../lib/errorLog.ts'

export function ErrorCenterPage() {
  const [rows, setRows] = useState<ClientError[]>(getErrorLog())
  const [selected, setSelected] = useState<ClientError | null>(null)
  useEffect(() => subscribeErrorLog(() => setRows([...getErrorLog()])), [])
  return (
    <div>
      <Breadcrumb items={[{ label: 'Error Center' }]} />
      <div className="page-head"><h2>Error Center</h2><p className="muted">Chỉ ghi lỗi client thực bắt được (API error / network). Không fake server errors. Mã hỗ trợ là correlationId nếu có.</p></div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button type="button" className="btn btn-sm" onClick={() => { clearErrorLog(); setSelected(null) }}>Xóa log</button>
        <span className="muted">{rows.length} bản ghi</span>
      </div>
      {rows.length === 0 ? <div className="empty"><div className="empty-title">Chưa có lỗi</div><p className="muted">Client chưa bắt được lỗi nào.</p></div> : (
        <div className="table-wrap"><table className="table"><thead><tr><th>Thời gian</th><th>Code</th><th>Status</th><th>Message</th><th>Source</th><th>Correlation</th><th></th></tr></thead><tbody>
          {rows.map((e) => (
            <tr key={e.id}>
              <td>{new Date(e.time).toLocaleString('vi-VN')}</td>
              <td><code>{e.code}</code></td>
              <td>{e.status}</td>
              <td style={{ maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.message}</td>
              <td>{e.source}</td>
              <td>{e.correlationId ? <code>{e.correlationId.slice(0, 12)}…</code> : '—'}</td>
              <td><button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelected(e)}>Chi tiết</button></td>
            </tr>
          ))}
        </tbody></table></div>
      )}
      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected ? `Lỗi #${selected.id}` : ''}>
        {selected ? (
          <div style={{ display: 'grid', gap: 8, fontSize: 14 }}>
            <div><b>Code:</b> {selected.code}</div>
            <div><b>Status:</b> {selected.status}</div>
            <div><b>Message:</b> {selected.message}</div>
            <div><b>Source:</b> {selected.source}</div>
            <div><b>Time:</b> {new Date(selected.time).toLocaleString('vi-VN')}</div>
            <div><b>Mã hỗ trợ:</b> {selected.correlationId ?? '—'}</div>
            {selected.correlationId ? <div className="muted">Gửi mã hỗ trợ này cho quản trị viên để tra cứu log.</div> : null}
            <pre className="code-block">{JSON.stringify(selected, null, 2)}</pre>
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}
