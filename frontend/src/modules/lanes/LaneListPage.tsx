import { t as translate } from "../../lib/i18n"
import { useMemo, useState } from 'react'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Dialog } from '../../components/ui/Dialog.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Table } from '../../components/ui/Table.tsx'
import { LaneForm } from './LaneForm.tsx'
import { useLanes } from './useLanes.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { can } from '../../lib/permissions.ts'

export function LaneListPage() {
  const { user } = useAuth()
  const { lanes, loading, error, refresh, createLane, updateLane, inactive } = useLanes()
  const [dir, setDir] = useState('ALL')
  const [status, setStatus] = useState('ALL')
  const [openCreate, setOpenCreate] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const [confirmInactive, setConfirmInactive] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [laneError, setLaneError] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return lanes.filter((l) => {
      if (dir !== 'ALL' && l.direction !== dir) return false
      if (status === 'ACTIVE' && !l.active) return false
      if (status === 'INACTIVE' && l.active) return false
      return true
    })
  }, [lanes, dir, status])

  if (loading) return <Spinner />
  if (error) {
    return (
      <div>
        <Alert variant="error">{error}</Alert>
        <Button type="button" onClick={() => void refresh()}>{translate("Thử lại")}</Button>
      </div>
    )
  }

  return (
    <div className="data-page lanes-page">
      <section className="data-hero data-hero--cream">
        <div className="data-hero-copy">
          <span className="data-kicker">Lane Management · Duy Anh</span>
          <h2>{translate("Quản lý làn")}</h2>
          <p>{translate("Cấu hình làn IN/OUT, nguồn video và trạng thái vận hành.")}</p>
        </div>
        {can(user, 'lanes.create') && <Button variant="primary" onClick={() => setOpenCreate(true)}>{translate("Tạo làn")}</Button>}
      </section>

      {feedback ? <Alert variant="success">{feedback}</Alert> : null}
      {laneError ? <Alert variant="error">{laneError}</Alert> : null}

      <section className="data-filter-card data-filter-card--compact">
        <span className="data-section-kicker">{translate("Bộ lọc làn xe")}</span>
        <div className="data-filter-grid data-filter-grid--two">
          <Select label="Direction" value={dir} onChange={(e) => setDir(e.target.value)}>
            <option value="ALL">ALL</option>
            <option value="IN">IN</option>
            <option value="OUT">OUT</option>
          </Select>
          <Select label="Status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="ALL">ALL</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
          </Select>
        </div>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title={translate("Chưa có làn nào")} description={lanes.length === 0 ? translate("Nhấn Tạo làn để thêm làn đầu tiên.") : translate("Không có làn phù hợp bộ lọc.")} />
      ) : (
        <section className="data-table-card">
          <div className="data-table-head">
            <div>
              <span className="data-section-kicker">GATE TOPOLOGY</span>
              <h3>{translate("Danh sách làn")}</h3>
            </div>
            <span className="data-table-meta">{filtered.length} / {lanes.length}</span>
          </div>
          <Table>
            <thead>
              <tr>
                <th>{translate("Tên làn")}</th>
                <th>Direction</th>
                <th>Video source</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((lane) => (
                <tr key={lane.id}>
                  <td className="data-lane">{lane.name}</td>
                  <td><span className={`badge ${lane.direction === 'IN' ? 'badge-info' : 'badge-warning'}`}>{lane.direction}</span></td>
                  <td className="data-mono">{lane.video_source ?? '-'}</td>
                  <td><span className={`badge ${lane.active ? 'badge-success' : 'badge-muted'}`}>{lane.active ? 'Active' : 'Inactive'}</span></td>
                  <td>
                    <div className="row-actions data-row-actions">
                      {can(user, 'lanes.update') && <Button type="button" onClick={() => setEditing(lane.id)}>{translate("Sửa")}</Button>}
                      {lane.active && can(user, 'lanes.manage') ? (
                        <Button type="button" variant="danger" onClick={() => setConfirmInactive(lane.id)}>{translate("Ngưng hoạt động")}</Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </section>
      )}

      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} title={translate("Tạo làn")}>
        <LaneForm
          onCancel={() => setOpenCreate(false)}
          onSubmit={async (payload) => {
            await createLane(payload)
            setOpenCreate(false)
            setFeedback(translate("Tạo làn thành công."))
            setTimeout(() => setFeedback(null), 3000)
          }}
        />
      </Dialog>

      {editing ? (
        (() => {
          const lane = lanes.find((l) => l.id === editing)
          if (!lane) return null
          return (
            <Dialog open={true} onClose={() => setEditing(null)} title={`Sửa làn ${lane.name}`}>
              <LaneForm
                initial={lane}
                onCancel={() => setEditing(null)}
                onSubmit={async (payload) => {
                  await updateLane(lane.id, payload)
                  setEditing(null)
                  setFeedback(translate("Cập nhật làn thành công."))
                  setTimeout(() => setFeedback(null), 3000)
                }}
              />
            </Dialog>
          )
        })()
      ) : null}

      <Dialog open={!!confirmInactive} onClose={() => setConfirmInactive(null)} title={translate("Xác nhận")}>
        <p>{translate("Bạn có chắc muốn ngưng hoạt động làn \"")}{lanes.find((l) => l.id === confirmInactive)?.name}&quot;?</p>
        {laneError ? <Alert variant="error">{laneError}</Alert> : null}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <Button type="button" onClick={() => setConfirmInactive(null)}>{translate("Hủy")}</Button>
          <Button
            type="button"
            variant="danger"
            onClick={async () => {
              if (!confirmInactive) return
              setLaneError(null)
              try {
                await inactive(confirmInactive)
                setConfirmInactive(null)
                setFeedback(translate("Đã ngưng hoạt động làn."))
                setTimeout(() => setFeedback(null), 3000)
              } catch (e) {
                setLaneError(e instanceof Error ? e.message : translate("Thao tác thất bại."))
              }
            }}
          >{translate("Xác nhận")}</Button>
        </div>
      </Dialog>
    </div>
  )
}
