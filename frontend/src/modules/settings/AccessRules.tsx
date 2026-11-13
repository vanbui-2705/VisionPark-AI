import { useEffect, useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { Alert } from '../../components/ui/Alert.tsx'

type AccessRule = {
  id: string
  normalized_plate: string | null
  ticket_code: string | null
  decision: 'ALLOW' | 'DENY'
  reason: string
  active: boolean
}

export function AccessRules() {
  const [rules, setRules] = useState<AccessRule[]>([])
  const [identifierType, setIdentifierType] = useState<'plate' | 'ticket'>('plate')
  const [identifier, setIdentifier] = useState('')
  const [decision, setDecision] = useState<'ALLOW' | 'DENY'>('DENY')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function refresh() {
    setRules(await apiClient.get<AccessRule[]>('/api/v1/tickets/access-rules'))
  }
  useEffect(() => { void refresh().catch(value => setError(value instanceof Error ? value.message : 'Không tải được quy tắc truy cập.')) }, [])

  async function createRule() {
    setBusy(true); setError(''); setNotice('')
    try {
      await apiClient.post('/api/v1/tickets/access-rules', {
        normalized_plate: identifierType === 'plate' ? identifier : null,
        ticket_code: identifierType === 'ticket' ? identifier : null,
        decision,
        reason,
      })
      setIdentifier(''); setReason(''); await refresh(); setNotice('Đã thêm quy tắc truy cập.')
    } catch (value) { setError(value instanceof Error ? value.message : 'Không lưu được quy tắc.') }
    finally { setBusy(false) }
  }

  async function toggle(rule: AccessRule) {
    setBusy(true); setError(''); setNotice('')
    try {
      await apiClient.patch(`/api/v1/tickets/access-rules/${rule.id}`, { active: !rule.active })
      await refresh(); setNotice(rule.active ? 'Đã ngừng áp dụng quy tắc.' : 'Đã kích hoạt quy tắc.')
    } catch (value) { setError(value instanceof Error ? value.message : 'Không cập nhật được quy tắc.') }
    finally { setBusy(false) }
  }

  return <section className="card card-polished stack">
    <div className="card-head"><div><span className="card-kicker">VEHICLE ACCESS CONTROL</span><h2>Danh sách cho phép / từ chối</h2></div></div>
    <p className="muted">Quy tắc được lưu riêng theo tòa nhà. Quy tắc từ chối sẽ chặn check-in trước khi mở barrier.</p>
    {error ? <Alert variant="error">{error}</Alert> : null}{notice ? <Alert variant="success">{notice}</Alert> : null}
    <form className="stack" onSubmit={event => { event.preventDefault(); void createRule() }}>
      <div className="form-grid">
        <label className="field"><span>Loại định danh</span><select value={identifierType} onChange={event => setIdentifierType(event.target.value as 'plate' | 'ticket')}><option value="plate">Biển số</option><option value="ticket">Mã vé/thẻ</option></select></label>
        <label className="field"><span>{identifierType === 'plate' ? 'Biển số' : 'Mã vé/thẻ'}</span><input required value={identifier} onChange={event => setIdentifier(event.target.value)} /></label>
        <label className="field"><span>Quyết định</span><select value={decision} onChange={event => setDecision(event.target.value as 'ALLOW' | 'DENY')}><option value="DENY">Từ chối</option><option value="ALLOW">Cho phép</option></select></label>
        <label className="field"><span>Lý do</span><input required minLength={3} maxLength={255} value={reason} onChange={event => setReason(event.target.value)} /></label>
      </div>
      <div><button className="btn btn-primary" disabled={busy || !identifier.trim() || reason.trim().length < 3}>Thêm quy tắc</button></div>
    </form>
    <div className="table-wrap"><table><thead><tr><th>Định danh</th><th>Quyết định</th><th>Lý do</th><th>Trạng thái</th><th></th></tr></thead><tbody>{rules.map(rule => <tr key={rule.id}><td className="data-mono">{rule.normalized_plate ?? rule.ticket_code}</td><td>{rule.decision === 'DENY' ? 'Từ chối' : 'Cho phép'}</td><td>{rule.reason}</td><td>{rule.active ? 'Đang áp dụng' : 'Đã tắt'}</td><td><button type="button" className="btn btn-sm" disabled={busy} onClick={() => void toggle(rule)}>{rule.active ? 'Tắt' : 'Bật'}</button></td></tr>)}</tbody></table></div>
    {!rules.length ? <p className="muted">Chưa có quy tắc truy cập.</p> : null}
  </section>
}
