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
    <div className="utility-page">
      <Breadcrumb items={[{ label: 'Error Center' }]} />

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Client Diagnostics · Duy Anh</span>
          <h1>Error Center</h1>
          <p>{translate("Lỗi thật được lưu trong database. Dùng mã hỗ trợ để tra cứu log hệ thống.")}</p>
        </div>
        <div className="utility-hero-stat">
          <strong>{rows.length}</strong>
          <span>{translate("bản ghi")}</span>
        </div>
      </section>

      <div className="row-actions" style={{ justifyContent: 'space-between' }}>
        <span className="muted" style={{ fontSize: 12 }}>{rows.length} {translate("bản ghi lỗi đã lưu")}</span>
        <button type="button" className="btn btn-sm" onClick={() => { clearErrorLog(); setSelected(null) }}>{translate("Làm mới")}</button>
      </div>

      {rows.length === 0 ? (
        <section className="utility-panel">
          <span className="utility-section-kicker">CLEAN STATE</span>
          <h3 style={{ margin: '6px 0 4px', fontWeight: 400 }}>{translate("Chưa có lỗi")}</h3>
          <p className="muted" style={{ margin: 0 }}>{translate("Client chưa bắt được lỗi nào.")}</p>
        </section>
      ) : (
        <section className="utility-table-panel">
          <div className="utility-panel-head">
            <div>
              <span className="utility-section-kicker">CAPTURED EXCEPTIONS</span>
              <h3>Client Error Log</h3>
            </div>
            <Badge variant="danger">{rows.length}</Badge>
          </div>
          <div className="utility-table-wrap">
            <table className="table utility-table">
              <thead><tr><th>{translate("Thời gian")}</th><th>Code</th><th>Status</th><th>Message</th><th>Source</th><th>Correlation</th><th></th></tr></thead>
              <tbody>{rows.map((e) => (
                <tr key={e.id}>
                  <td className="data-time">{new Date(e.time).toLocaleString('vi-VN')}</td>
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
        </section>
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
