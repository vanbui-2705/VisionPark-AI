import { useAuth } from '../auth/AuthContext.tsx'
import { useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { PreferencesEditor } from './PreferencesEditor.tsx'
import { PricingSettings } from './PricingSettings.tsx'
import { MonthlyTickets } from './MonthlyTickets.tsx'
import { Link } from 'react-router-dom'

export function SettingsPage() {
  const { user } = useAuth()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [notice, setNotice] = useState('')
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN' || (user?.role as string) === 'ADMIN'
  const isBuildingAdmin = user?.role === 'BUILDING_ADMIN'
  const hasBuildingContext = isBuildingAdmin && Boolean(user?.building_id)
  return <div className="data-page">
    <PreferencesEditor />
    {isSystemAdmin && <section className="card card-polished">
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
    {isSystemAdmin && <section className="card card-polished settings-context-empty" aria-labelledby="building-settings-title">
      <span className="card-kicker">CẤU HÌNH THEO TÒA NHÀ</span>
      <h2 id="building-settings-title">Giá vé và vé tháng</h2>
      <p>API cấu hình giá hiện chỉ cho phép tài khoản <strong>BUILDING_ADMIN</strong> thao tác trong tòa nhà được gán. Hãy tạo tòa nhà và gán tài khoản quản lý tòa nhà trước khi cấu hình.</p>
      <Link className="btn" to="/admin/users">Quản lý tài khoản và phân công tòa nhà</Link>
    </section>}
    {isBuildingAdmin && !hasBuildingContext && <section className="card card-polished settings-context-empty" role="status">
      <span className="card-kicker">CHƯA CÓ PHẠM VI TÒA NHÀ</span>
      <h2>Chưa thể tải cấu hình vận hành</h2>
      <p>Tài khoản này chưa được gán tòa nhà. Liên hệ SYSTEM_ADMIN để hoàn tất phân công trước khi cấu hình giá và vé tháng.</p>
    </section>}
    {hasBuildingContext && <PricingSettings />}
    {hasBuildingContext && <MonthlyTickets />}
  </div>
}
