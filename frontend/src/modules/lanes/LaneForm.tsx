import { useState } from 'react'
import type { Lane, LaneDirection } from '../../api/types.ts'
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
  onSubmit: (payload: { name: string; direction: LaneDirection; video_source?: string | null; active?: boolean }) => Promise<void>
  onCancel: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [direction, setDirection] = useState<LaneDirection>((initial?.direction as LaneDirection) ?? 'IN')
  const [videoSource, setVideoSource] = useState(initial?.video_source ?? '')
  const [active, setActive] = useState(initial?.active ?? true)
  const [err, setErr] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const dirty =
    name !== (initial?.name ?? '') ||
    direction !== ((initial?.direction as LaneDirection) ?? 'IN') ||
    videoSource !== (initial?.video_source ?? '') ||
    active !== (initial?.active ?? true)
  useUnsavedGuard(dirty)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) { setErr('Tên làn không được để trống'); return }
    if (direction !== 'IN' && direction !== 'OUT') { setErr('Direction phải là IN hoặc OUT'); return }
    setErr(null)
    setSubmitting(true)
    try {
      await onSubmit({ name: trimmed, direction, video_source: videoSource.trim() || null, active })
    } catch (e2) {
      if (e2 instanceof ApiError && e2.code === 'DUPLICATE_LANE_NAME') setErr('Tên làn đã tồn tại.')
      else if (e2 instanceof ApiError) setErr(e2.message)
      else if (e2 instanceof Error) setErr(e2.message)
      else setErr('Thao tác thất bại.')
    } finally { setSubmitting(false) }
  }

  return (
    <form onSubmit={submit}>
      {err ? <Alert variant="error">{err}</Alert> : null}
      <Input label="Tên làn *" name="name" value={name} onChange={(e) => setName(e.target.value)} />
      <Select label="Direction" name="direction" value={direction} onChange={(e) => setDirection(e.target.value as LaneDirection)}>
        <option value="IN">IN</option>
        <option value="OUT">OUT</option>
      </Select>
      <Input label="Video source" name="video_source" value={videoSource} onChange={(e) => setVideoSource(e.target.value)} placeholder="optional" />
      <label style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 12 }}>
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Active
      </label>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <Button type="button" onClick={onCancel}>Hủy</Button>
        <Button type="submit" variant="primary" loading={submitting}>Lưu</Button>
      </div>
    </form>
  )
}
