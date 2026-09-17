import { useEffect, useState } from 'react'
import { useAuth } from '../../modules/auth/AuthContext.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Button } from '../../components/ui/Button.tsx'
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
    <div>
      <Breadcrumb items={[{ label: 'Cài đặt' }]} />
      <h2>Cài đặt</h2>
      <p className="muted">Chỉ lưu frontend-local (localStorage). Không ghi lên backend.</p>
      {ok ? <Alert variant="success">{ok}</Alert> : null}
      <div className="card" style={{ maxWidth: 560 }}>
        <Input label="Tên hiển thị (local)" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        <label className="field"><span>Giao diện</span><select value={theme} onChange={(e) => setTheme(e.target.value)}><option value="light">Sáng</option><option value="dark">Tối</option></select></label>
        <label className="field"><span>Ngôn ngữ</span><select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}><Button onClick={onSave} variant="primary">Lưu</Button></div>
      </div>
    </div>
  )
}
