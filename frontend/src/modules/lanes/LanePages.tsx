import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { lanesApi } from '../../api/lanesApi.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { can } from '../../lib/permissions.ts'
import type { Lane } from '../../api/types.ts'
import { LaneForm } from './LaneForm.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

export function LaneCreatePage() {
  const nav = useNavigate()
  const [done, setDone] = useState(false)
  useEffect(() => { if (done) nav('/admin/lanes') }, [done, nav])
  const onSubmit = async (payload: { name: string; direction: Lane['direction']; video_source?: string | null; active?: boolean }) => {
    await lanesApi.createLane(payload)
    setDone(true)
  }
  return (
    <div>
      <Breadcrumb items={[{ label: translate("Làn xe"), to: '/admin/lanes' }, { label: translate("Tạo làn xe") }]} />
      <h2>{translate("Tạo làn xe")}</h2>
      <div className="card" style={{ maxWidth: 560 }}><LaneForm onSubmit={onSubmit} onCancel={() => nav('/admin/lanes')} /></div>
    </div>
  )
}
export function LaneEditPage() {
  const nav = useNavigate()
  const { id = '' } = useParams()
  const [lane, setLane] = useState<Lane | null>(null)
  useEffect(() => { lanesApi.getLane(id).then(setLane).catch(() => {}) }, [id])
  if (!lane) return <div className="spinner">{translate("Đang tải...")}</div>
  const onSubmit = async (payload: { name: string; direction: Lane['direction']; video_source?: string | null; active?: boolean }) => {
    await lanesApi.updateLane(id, payload)
    nav(`/admin/lanes/${id}`)
  }
  return (
    <div>
      <Breadcrumb items={[{ label: translate("Làn xe"), to: '/admin/lanes' }, { label: lane.name, to: `/admin/lanes/${id}` }, { label: translate("Chỉnh sửa") }]} />
      <h2>{translate("Chỉnh sửa làn xe")}</h2>
      <div className="card" style={{ maxWidth: 560 }}><LaneForm initial={lane} onSubmit={onSubmit} onCancel={() => nav(`/admin/lanes/${id}`)} /></div>
    </div>
  )
}
export function LaneDetailPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const [lane, setLane] = useState<Lane | null>(null)
  const nav = useNavigate()
  useEffect(() => { lanesApi.getLane(id).then(setLane).catch(() => {}) }, [id])
  if (!lane) return <div className="spinner">{translate("Đang tải...")}</div>
  return (
    <div>
      <Breadcrumb items={[{ label: translate("Làn xe"), to: '/admin/lanes' }, { label: lane.name }]} />
      <div className="page-head"><h2>{lane.name}</h2><p className="muted">{lane.direction} · {lane.active ? translate("Hoạt động") : translate("Tạm dừng")}</p></div>
      <div className="card">
        <ul className="kv"><li><b>ID:</b> {lane.id}</li><li><b>Video source:</b> {lane.video_source ?? '—'}</li></ul>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          {can(user, 'lanes.update') && <button className="btn btn-primary" onClick={() => nav(`/admin/lanes/${id}/edit`)}>{translate("Chỉnh sửa")}</button>}
          <button className="btn" onClick={() => nav('/admin/lanes')}>{translate("Quay lại")}</button>
        </div>
      </div>
    </div>
  )
}
