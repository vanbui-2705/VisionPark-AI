import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { apiClient } from '../../api/client'
import { applyPreferences, loadPreferences, type Preferences } from '../../lib/preferences'
import { Alert } from '../../components/ui/Alert'
export function PreferencesEditor() {
  const [pref, setPref] = useState<Preferences>({ theme: 'light', language: 'vi' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { loadPreferences().then(setPref).catch(e => setError(e.message)) }, [])
  const save = async () => {
    setBusy(true); setError(''); setMessage('')
    try { const p = await apiClient.put<Preferences>('/api/v1/auth/preferences', pref); applyPreferences(p); setMessage(translate("Đã lưu cài đặt.")) }
    catch (e) { setError(e instanceof Error ? e.message : translate("Lưu thất bại.")) }
    finally { setBusy(false) }
  }
  return <section className="card card-polished">
    <div className="card-head">
      <div>
        <span className="card-kicker">WORKSPACE PREFERENCES</span>
        <h2>{translate("Cài đặt")}</h2>
      </div>
    </div>
    {error && <Alert variant="error">{error}</Alert>}
    {message && <Alert variant="success">{message}</Alert>}
    <div className="form-grid" style={{ maxWidth: 640 }}>
      <label className="field"><span>{translate("Giao diện")}</span><select value={pref.theme} disabled={busy} onChange={e => setPref({ ...pref, theme: e.target.value as Preferences['theme'] })}><option value="light">{translate("Sáng")}</option><option value="dark">{translate("Tối")}</option></select></label>
      <label className="field"><span>{translate("Ngôn ngữ")}</span><select value={pref.language} disabled={busy} onChange={e => setPref({ ...pref, language: e.target.value as Preferences['language'] })}><option value="vi">{translate("Tiếng Việt")}</option><option value="en">English</option></select></label>
    </div>
    <div className="row-actions" style={{ marginTop: 16 }}>
      <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void save()}>{translate("Lưu")}</button>
    </div>
  </section>
}
