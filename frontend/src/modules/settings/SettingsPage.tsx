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
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Cài đặt' }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Preferences · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Cài đặt</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Chỉ lưu frontend-local (localStorage). Không ghi lên backend.</p>
        </div>
        <Badge>Local only</Badge>
      </div>
      {ok ? <Alert variant="success">{ok}</Alert> : null}
      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, maxWidth: 560, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ display: 'grid', gap: 12 }}>
          <Input label="Tên hiển thị (local)" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          <label className="field"><span>Giao diện</span><select value={theme} onChange={(e) => setTheme(e.target.value)}><option value="light">Sáng</option><option value="dark">Tối</option></select></label>
          <label className="field"><span>Ngôn ngữ</span><select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}><Button onClick={onSave} variant="primary">Lưu</Button></div>
      </section>
    </div>
  )
}
