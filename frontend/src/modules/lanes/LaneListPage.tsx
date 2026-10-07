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
    <div className="data-page lanes-page">
      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">Cổng kiểm soát · VisionPark</span>
          <h2>Quản lý làn</h2>
          <p>Cấu hình làn vào/ra, nguồn luồng camera và trạng thái vận hành.</p>
        </div>
        <Button variant="secondary" onClick={() => setOpenCreate(true)}>Tạo làn</Button>
      </section>

      {feedback ? <Alert variant="success">{feedback}</Alert> : null}
      {laneError ? <Alert variant="error">{laneError}</Alert> : null}

      <section className="data-filter-card data-filter-card--compact">
        <div className="data-section-kicker">Bộ lọc vận hành</div>
        <div className="data-filter-grid data-filter-grid--two">
        <Select label="Hướng làn" value={dir} onChange={(e) => setDir(e.target.value)}>
          <option value="ALL">Tất cả</option>
          <option value="IN">Làn vào</option>
          <option value="OUT">Làn ra</option>
        </Select>
        <Select label="Trạng thái" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="ALL">Tất cả</option>
          <option value="ACTIVE">Đang hoạt động</option>
          <option value="INACTIVE">Ngưng hoạt động</option>
        </Select>
        </div>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title="Chưa có làn nào" description={lanes.length === 0 ? 'Nhấn Tạo làn để thêm làn đầu tiên.' : 'Không có làn phù hợp bộ lọc.'} />
      ) : (
        <section className="data-table-card">
        <div className="data-table-head">
          <div><span className="data-section-kicker">LANE MONITOR</span><h3>Danh sách làn</h3></div>
          <span className="data-table-meta">{filtered.length} / {lanes.length} làn</span>
        </div>
        <Table>
          <thead>
            <tr>
              <th>Tên làn</th>
              <th>Hướng</th>
              <th>Nguồn video</th>
              <th>Trạng thái</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((lane) => (
              <tr key={lane.id}>
                <td><strong>{lane.name}</strong></td>
                <td>{lane.direction === 'IN' ? 'Làn vào' : lane.direction === 'OUT' ? 'Làn ra' : lane.direction}</td>
                <td style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>{lane.video_source ?? '—'}</td>
                <td><span className={`badge ${lane.active ? 'badge-success' : 'badge-muted'}`}>{lane.active ? 'Đang hoạt động' : 'Ngưng hoạt động'}</span></td>
                <td>
                  <div className="row-actions data-row-actions">
                    <Button type="button" variant="secondary" onClick={() => setEditing(lane.id)}>Sửa</Button>
                    {lane.active ? (
                      <Button type="button" variant="danger" onClick={() => setConfirmInactive(lane.id)}>Ngưng hoạt động</Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
        </section>
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
        <div className="data-dialog-actions">
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
