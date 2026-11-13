import { t as translate } from "../../lib/i18n"
import { useState } from 'react'
import type { Lane, LaneDirection } from '../../api/types.ts'
import type { LanePayload } from '../../api/lanesApi.ts'
import { ApiError } from '../../api/errors.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { useUnsavedGuard } from '../../hooks/useUnsavedGuard.ts'

export function LaneForm({
  initial,
  onSubmit,
  onCancel,
}: {
  initial?: Partial<Lane>
  onSubmit: (payload: LanePayload) => Promise<void>
  onCancel: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [direction, setDirection] = useState<LaneDirection>((initial?.direction as LaneDirection) ?? 'IN')
  const initialSourceMode = initial?.video_source && initial.video_source !== 'FILE_UPLOAD' ? 'RTSP' : 'FILE_UPLOAD'
  const [sourceMode, setSourceMode] = useState<'FILE_UPLOAD' | 'RTSP'>(initialSourceMode)
  const [videoSource, setVideoSource] = useState(initialSourceMode === 'RTSP' ? initial?.video_source ?? '' : '')
  const [allowedVehicleTypes, setAllowedVehicleTypes] = useState<Array<'CAR' | 'MOTORBIKE' | 'BICYCLE'>>(
    initial?.allowed_vehicle_types?.length ? initial.allowed_vehicle_types : ['CAR', 'MOTORBIKE', 'BICYCLE'],
  )
  const [cameraId, setCameraId] = useState(initial?.camera_id ?? '')
  const [barrierId, setBarrierId] = useState(initial?.barrier_id ?? '')
  const [active, setActive] = useState(initial?.active ?? true)
  const [err, setErr] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const dirty =
    name !== (initial?.name ?? '') ||
    direction !== ((initial?.direction as LaneDirection) ?? 'IN') ||
    sourceMode !== initialSourceMode ||
    videoSource !== (initialSourceMode === 'RTSP' ? initial?.video_source ?? '' : '') ||
    allowedVehicleTypes.join(',') !== (initial?.allowed_vehicle_types ?? ['CAR', 'MOTORBIKE', 'BICYCLE']).join(',') ||
    cameraId !== (initial?.camera_id ?? '') ||
    barrierId !== (initial?.barrier_id ?? '') ||
    active !== (initial?.active ?? true)
  useUnsavedGuard(dirty)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) { setErr(translate("Tên làn không được để trống")); return }
    if (direction !== 'IN' && direction !== 'OUT') { setErr(translate("Direction phải là IN hoặc OUT")); return }
    if (sourceMode === 'RTSP' && !videoSource.trim()) { setErr('Nhập URL RTSP cho camera của làn.'); return }
    if (!allowedVehicleTypes.length) { setErr('Chọn ít nhất một loại xe được phép.'); return }
    setErr(null)
    setSubmitting(true)
    try {
      await onSubmit({
        name: trimmed,
        direction,
        video_source: sourceMode === 'FILE_UPLOAD' ? 'FILE_UPLOAD' : videoSource.trim(),
        allowed_vehicle_types: allowedVehicleTypes,
        camera_id: cameraId.trim() || null,
        barrier_id: barrierId.trim() || null,
        active,
      })
    } catch (e2) {
      if (e2 instanceof ApiError && e2.code === 'DUPLICATE_LANE_NAME') setErr(translate("Tên làn đã tồn tại."))
      else if (e2 instanceof ApiError) setErr(e2.message)
      else if (e2 instanceof Error) setErr(e2.message)
      else setErr(translate("Thao tác thất bại."))
    } finally { setSubmitting(false) }
  }

  return (
    <form onSubmit={submit}>
      {err ? <Alert variant="error">{err}</Alert> : null}
      <Input label={translate("Tên làn *")} name="name" value={name} onChange={(e) => setName(e.target.value)} />
      <Select label="Direction" name="direction" value={direction} onChange={(e) => setDirection(e.target.value as LaneDirection)}>
        <option value="IN">IN</option>
        <option value="OUT">OUT</option>
      </Select>
      <Select label="Nguồn nhận diện" name="source_mode" value={sourceMode} onChange={(e) => setSourceMode(e.target.value as 'FILE_UPLOAD' | 'RTSP')}>
        <option value="FILE_UPLOAD">Tải ảnh / video tại Station</option>
        <option value="RTSP">Camera RTSP (chưa tích hợp runtime)</option>
      </Select>
      {sourceMode === 'RTSP' ? <Input label="URL RTSP *" name="video_source" value={videoSource} onChange={(e) => setVideoSource(e.target.value)} placeholder="rtsp://camera/lane" /> : null}
      <fieldset className="field" style={{ marginBottom: 12 }}>
        <legend>Loại xe được phép *</legend>
        {(['CAR', 'MOTORBIKE', 'BICYCLE'] as const).map((vehicleType) => <label key={vehicleType} style={{ display: 'inline-flex', gap: 6, alignItems: 'center', marginRight: 14 }}>
          <input type="checkbox" checked={allowedVehicleTypes.includes(vehicleType)} onChange={(event) => setAllowedVehicleTypes((current) => event.target.checked ? [...current, vehicleType] : current.filter((item) => item !== vehicleType))} />
          {vehicleType === 'CAR' ? 'Ô tô' : vehicleType === 'MOTORBIKE' ? 'Xe máy' : 'Xe đạp'}
        </label>)}
      </fieldset>
      <Input label="Mã camera" name="camera_id" value={cameraId} onChange={(e) => setCameraId(e.target.value)} placeholder="Không bắt buộc" />
      <Input label="Mã barrier" name="barrier_id" value={barrierId} onChange={(e) => setBarrierId(e.target.value)} placeholder="Không bắt buộc · hiện đang mô phỏng" />
      <label style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 12 }}>
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Active
      </label>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <Button type="button" onClick={onCancel}>{translate("Hủy")}</Button>
        <Button type="submit" variant="primary" loading={submitting}>{translate("Lưu")}</Button>
      </div>
    </form>
  )
}
