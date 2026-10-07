import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Drawer } from '../../components/ui/Drawer.tsx'
import { getErrorLog, clearErrorLog, subscribeErrorLog, type ClientError } from '../../lib/errorLog.ts'

export function ErrorCenterPage() {
  const [rows, setRows] = useState<ClientError[]>(getErrorLog())
  const [selected, setSelected] = useState<ClientError | null>(null)
  useEffect(() => subscribeErrorLog(() => setRows([...getErrorLog()])), [])

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Error Center' }]} />

      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Client Diagnostics · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Error Center</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{translate("Lỗi thật được lưu trong database. Dùng mã hỗ trợ để tra cứu log hệ thống.")}</p>
        </div>
        <Badge variant={rows.length ? 'danger' : 'success'}>{rows.length}{translate("bản ghi")}</Badge>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-sm" onClick={() => { clearErrorLog(); setSelected(null) }}>{translate("Làm mới")}</button>
        <span className="muted" style={{ fontSize: 12 }}>{rows.length}{translate("bản ghi lỗi đã lưu")}</span>
      </div>

      {rows.length === 0 ? (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}><div style={{ fontWeight: 700 }}>{translate("Chưa có lỗi")}</div><p className="muted" style={{ margin: '6px 0 0' }}>{translate("Client chưa bắt được lỗi nào.")}</p></div>
      ) : (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden', boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <div style={{ overflow: 'auto' }}>
            <table className="table" style={{ margin: 0 }}>
              <thead><tr><th>{translate("Thời gian")}</th><th>Code</th><th>Status</th><th>Message</th><th>Source</th><th>Correlation</th><th></th></tr></thead>
              <tbody>{rows.map((e) => (
                <tr key={e.id}>
                  <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>{new Date(e.time).toLocaleString('vi-VN')}</td>
                  <td><code>{e.code}</code></td>
                  <td>{String(e.status)}</td>
                  <td style={{ maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.message}</td>
                  <td>{e.source}</td>
                  <td>{e.correlationId ? <code>{e.correlationId.slice(0, 12)}…</code> : '—'}</td>
                  <td><button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelected(e)}>{translate("Chi tiết")}</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}

      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected ? `Lỗi #${selected.id}` : ''}>
        {selected ? (
          <div style={{ display: 'grid', gap: 8, fontSize: 13 }}>
            <div><b>Code:</b> {selected.code}</div><div><b>Status:</b> {selected.status}</div><div><b>Message:</b> {selected.message}</div><div><b>Source:</b> {selected.source}</div><div><b>Time:</b> {new Date(selected.time).toLocaleString('vi-VN')}</div><div><b>{translate("Mã hỗ trợ:")}</b> {selected.correlationId ?? '—'}</div>
            {selected.correlationId ? <div className="muted">{translate("Gửi mã hỗ trợ này cho quản trị viên để tra cứu log.")}</div> : null}
            <pre className="code-block">{JSON.stringify(selected, null, 2)}</pre>
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}
