import { useAuth } from '../auth/AuthContext.tsx'
import { useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { PreferencesEditor } from './PreferencesEditor.tsx'
import { PricingSettings } from './PricingSettings.tsx'

export function SettingsPage() {
  const { user } = useAuth()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [notice, setNotice] = useState('')
  return <div className="data-page">
    <PreferencesEditor />
    {(user?.role === 'SYSTEM_ADMIN' || (user?.role as string) === 'ADMIN') && <section className="card card-polished">
      <div className="card-head">
        <div>
          <span className="card-kicker">HẠ TẦNG TÒA NHÀ</span>
          <h2>Tòa nhà</h2>
        </div>
      </div>
      <form className="stack" onSubmit={e => {
        e.preventDefault(); setNotice('')
        void apiClient.post('/api/v1/buildings', { code, name })
          .then(() => { setCode(''); setName(''); setNotice('Đã tạo tòa nhà.') })
          .catch(err => setNotice(err instanceof Error ? err.message : 'Tạo tòa nhà thất bại.'))
      }}>
        <div className="form-grid" style={{ maxWidth: 640 }}>
          <label className="field"><span>Mã tòa nhà</span><input required value={code} onChange={e => setCode(e.target.value)} /></label>
          <label className="field"><span>Tên tòa nhà</span><input required value={name} onChange={e => setName(e.target.value)} /></label>
        </div>
        <div className="row-actions">
          <button className="btn btn-primary">Tạo tòa nhà</button>
        </div>
      </form>
      {notice && <p role="status" className="alert alert-info" style={{ marginTop: 12 }}>{notice}</p>}
    </section>}
    {(user?.role === 'BUILDING_ADMIN' || user?.role === 'SYSTEM_ADMIN' || (user?.role as string) === 'ADMIN') && <PricingSettings />}
  </div>
}
