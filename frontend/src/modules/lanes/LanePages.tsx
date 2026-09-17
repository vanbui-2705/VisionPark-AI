import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../api/client.ts'
import type { Lane } from '../../api/types.ts'
import { LaneForm } from './LaneForm.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

export function LaneCreatePage() {
  const nav = useNavigate()
  const [done, setDone] = useState(false)
  useEffect(() => { if (done) nav('/admin/lanes') }, [done, nav])
  const onSubmit = async (payload: { name: string; direction: Lane['direction']; video_source?: string | null; active?: boolean }) => {
    await apiClient.post('/api/v1/lanes', payload)
    setDone(true)
  }
  return (
    <div>
      <Breadcrumb items={[{ label: 'Làn xe', to: '/admin/lanes' }, { label: 'Tạo làn xe' }]} />
      <h2>Tạo làn xe</h2>
      <div className="card" style={{ maxWidth: 560 }}><LaneForm onSubmit={onSubmit} onCancel={() => nav('/admin/lanes')} /></div>
    </div>
  )
}
export function LaneEditPage() {
  const nav = useNavigate()
  const id = location.pathname.split('/')[3]
  const [lane, setLane] = useState<Lane | null>(null)
  useEffect(() => { apiClient.get<Lane>(`/api/v1/lanes/${id}`).then(setLane).catch(() => {}) }, [id])
  if (!lane) return <div className="spinner">Đang tải...</div>
  const onSubmit = async (payload: { name: string; direction: Lane['direction']; video_source?: string | null; active?: boolean }) => {
    await apiClient.patch(`/api/v1/lanes/${id}`, payload)
    nav(`/admin/lanes/${id}`)
  }
  return (
    <div>
      <Breadcrumb items={[{ label: 'Làn xe', to: '/admin/lanes' }, { label: lane.name, to: `/admin/lanes/${id}` }, { label: 'Chỉnh sửa' }]} />
      <h2>Chỉnh sửa làn xe</h2>
      <div className="card" style={{ maxWidth: 560 }}><LaneForm initial={lane} onSubmit={onSubmit} onCancel={() => nav(`/admin/lanes/${id}`)} /></div>
    </div>
  )
}
export function LaneDetailPage() {
  const id = location.pathname.split('/')[3]
  const [lane, setLane] = useState<Lane | null>(null)
  const nav = useNavigate()
  useEffect(() => { apiClient.get<Lane>(`/api/v1/lanes/${id}`).then(setLane).catch(() => {}) }, [id])
  if (!lane) return <div className="spinner">Đang tải...</div>
  return (
    <div>
      <Breadcrumb items={[{ label: 'Làn xe', to: '/admin/lanes' }, { label: lane.name }]} />
      <div className="page-head"><h2>{lane.name}</h2><p className="muted">{lane.direction} · {lane.active ? 'Hoạt động' : 'Tạm dừng'}</p></div>
      <div className="card">
        <ul className="kv"><li><b>ID:</b> {lane.id}</li><li><b>Video source:</b> {lane.video_source ?? '—'}</li></ul>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={() => nav(`/admin/lanes/${id}/edit`)}>Chỉnh sửa</button>
          <button className="btn" onClick={() => nav('/admin/lanes')}>Quay lại</button>
        </div>
      </div>
    </div>
  )
}
