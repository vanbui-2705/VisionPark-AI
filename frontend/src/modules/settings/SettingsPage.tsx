import { useEffect, useState } from 'react'
import { useAuth } from '../../modules/auth/AuthContext.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

export function SettingsPage() {
  const { user } = useAuth()
  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [theme, setTheme] = useState(localStorage.getItem('vp.theme') ?? 'light')
  const [language, setLanguage] = useState(localStorage.getItem('vp.language') ?? 'vi')
  const [ok, setOk] = useState<string | null>(null)

  useEffect(() => { setDisplayName(user?.display_name ?? '') }, [user?.display_name])

  const onSave = () => {
    localStorage.setItem('vp.theme', theme)
    localStorage.setItem('vp.language', language)
    localStorage.setItem('vp.display_name', displayName)
    setOk('Đã lưu cài đặt (chỉ lưu local — frontend preferences).')
    setTimeout(() => setOk(null), 2500)
  }

  return (
    <div className="data-page settings-page">
      <Breadcrumb items={[{ label: 'Cài đặt' }]} />
      <section className="data-hero data-hero--forest settings-hero">
        <div>
          <span className="data-kicker">Tùy chọn hiển thị · VisionPark</span>
          <h2>Cài đặt</h2>
          <p>Lưu tùy chọn cá nhân trên trình duyệt hiện tại.</p>
        </div>
        <Badge>Thiết bị này</Badge>
      </section>
      {ok ? <Alert variant="success">{ok}</Alert> : null}
      <section className="data-filter-card settings-form">
        <div className="settings-fields">
          <Input label="Tên hiển thị cá nhân" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          <label className="field"><span>Chế độ giao diện</span><select value={theme} onChange={(e) => setTheme(e.target.value)}><option value="light">Sáng</option><option value="dark">Tối</option></select></label>
          <label className="field"><span>Ngôn ngữ hiển thị</span><select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
        </div>
        <div className="settings-actions"><Button onClick={onSave} variant="primary">Lưu thay đổi</Button></div>
      </section>
    </div>
  )
}
