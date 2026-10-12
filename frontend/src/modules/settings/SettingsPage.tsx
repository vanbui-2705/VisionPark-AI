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
  return <>
    <PreferencesEditor />
    {user?.role === 'SYSTEM_ADMIN' && <section className="card">
      <h2>Tòa nhà</h2>
      <form onSubmit={e => {
        e.preventDefault(); setNotice('')
        void apiClient.post('/api/v1/buildings', { code, name })
          .then(() => { setCode(''); setName(''); setNotice('Đã tạo tòa nhà.') })
          .catch(err => setNotice(err instanceof Error ? err.message : 'Tạo tòa nhà thất bại.'))
      }}>
        <label>Mã tòa nhà<input required value={code} onChange={e => setCode(e.target.value)} /></label>
        <label>Tên tòa nhà<input required value={name} onChange={e => setName(e.target.value)} /></label>
        <button className="btn btn-primary">Tạo tòa nhà</button>
      </form>
      {notice && <p role="status">{notice}</p>}
    </section>}
    {user?.role === 'BUILDING_ADMIN' && <PricingSettings />}
  </>
}
