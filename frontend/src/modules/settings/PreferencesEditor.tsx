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
  return <section className="card"><h2>{translate("Cài đặt")}</h2>
    {error && <Alert variant="error">{error}</Alert>}{message && <Alert variant="success">{message}</Alert>}
    <label>{translate("Giao diện")}<select value={pref.theme} disabled={busy} onChange={e => setPref({ ...pref, theme: e.target.value as Preferences['theme'] })}><option value="light">{translate("Sáng")}</option><option value="dark">{translate("Tối")}</option></select></label>
    <label>{translate("Ngôn ngữ")}<select value={pref.language} disabled={busy} onChange={e => setPref({ ...pref, language: e.target.value as Preferences['language'] })}><option value="vi">{translate("Tiếng Việt")}</option><option value="en">English</option></select></label>
    <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void save()}>{translate("Lưu")}</button>
  </section>
}
