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

export function LaneListPage() {
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
        <Button type="button" onClick={() => void refresh()}>Thử lại</Button>
      </div>
    )
  }

  return (
    <div>
      <div className="admin-topbar">
        <h2>Quản lý làn</h2>
        <Button variant="primary" onClick={() => setOpenCreate(true)}>Tạo làn</Button>
      </div>

      {feedback ? <Alert variant="success">{feedback}</Alert> : null}
      {laneError ? <Alert variant="error">{laneError}</Alert> : null}

      <div className="filters">
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

      {filtered.length === 0 ? (
        <EmptyState title="Chưa có làn nào" description={lanes.length === 0 ? 'Nhấn Tạo làn để thêm làn đầu tiên.' : 'Không có làn phù hợp bộ lọc.'} />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Tên làn</th>
              <th>Direction</th>
              <th>Video source</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((lane) => (
              <tr key={lane.id}>
                <td>{lane.name}</td>
                <td>{lane.direction}</td>
                <td>{lane.video_source ?? '-'}</td>
                <td>{lane.active ? 'Active' : 'Inactive'}</td>
                <td>
                  <div className="row-actions">
                    <Button type="button" onClick={() => setEditing(lane.id)}>Sửa</Button>
                    {lane.active ? (
                      <Button type="button" variant="danger" onClick={() => setConfirmInactive(lane.id)}>Ngưng hoạt động</Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} title="Tạo làn">
        <LaneForm
          onCancel={() => setOpenCreate(false)}
          onSubmit={async (payload) => {
            await createLane(payload)
            setOpenCreate(false)
            setFeedback('Tạo làn thành công.')
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
                  setFeedback('Cập nhật làn thành công.')
                  setTimeout(() => setFeedback(null), 3000)
                }}
              />
            </Dialog>
          )
        })()
      ) : null}

      <Dialog open={!!confirmInactive} onClose={() => setConfirmInactive(null)} title="Xác nhận">
        <p>Bạn có chắc muốn ngưng hoạt động làn &quot;{lanes.find((l) => l.id === confirmInactive)?.name}&quot;?</p>
        {laneError ? <Alert variant="error">{laneError}</Alert> : null}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <Button type="button" onClick={() => setConfirmInactive(null)}>Hủy</Button>
          <Button
            type="button"
            variant="danger"
            onClick={async () => {
              if (!confirmInactive) return
              setLaneError(null)
              try {
                await inactive(confirmInactive)
                setConfirmInactive(null)
                setFeedback('Đã ngưng hoạt động làn.')
                setTimeout(() => setFeedback(null), 3000)
              } catch (e) {
                setLaneError(e instanceof Error ? e.message : 'Thao tác thất bại.')
              }
            }}
          >
            Xác nhận
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
