import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import type { Lane } from '../../api/types.ts'
import type { DetectionResult } from '../station/types.ts'
import { DetectionImage } from '../../components/DetectionImage.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Select } from '../../components/ui/Select.tsx'

export function AlprTestPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [lanes, setLanes] = useState<Lane[]>([])
  const [lane, setLane] = useState('')
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [captureId, setCaptureId] = useState(() => crypto.randomUUID())
  useEffect(() => {
    lanesApi.getActiveLanes().then(setLanes).catch(error => setError(error instanceof Error ? error.message : translate("Không tải được làn xe.")))
  }, [])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  const run = async (persist = false) => {
    if (!file || !lane) return
    setLoading(true); setError(null); setResult(null)
    try {
      const form = new FormData()
      form.append('image', file)
      form.append('lane_id', lane)
      form.append('mode', persist ? 'final' : 'preview')
      form.append('persist', persist ? 'true' : 'false')
      form.append('input_kind', 'IMAGE_UPLOAD')
      if (persist) form.append('capture_id', captureId)
      setResult(await apiClient.postMultipart<DetectionResult>('/api/v1/alpr/detections', form, { timeoutMs: 60000 }))
    } catch (error) { setError(error instanceof Error ? error.message : translate("Nhận diện thất bại.")) }
    finally { setLoading(false) }
  }
  const bbox = result?.bbox
  return <section>
    <h2>{translate("Kiểm tra ALPR")}</h2>
    <p>{translate("Gửi ảnh tới provider đang chạy trên backend. Preview không lưu detection hoặc tạo check-in.")}</p>
    {error && <Alert variant="error">{error}</Alert>}
    <div className="card">
      <label>{translate("Ảnh đầu vào")}<input type="file" accept="image/jpeg,image/png" disabled={loading} onChange={event => { const selected = event.target.files?.[0] ?? null; setFile(selected); setPreview(selected ? URL.createObjectURL(selected) : ''); setResult(null); setCaptureId(crypto.randomUUID()); }} /></label>
      <Select label="Lane" value={lane} disabled={loading} onChange={event => { setLane(event.target.value); setResult(null); setCaptureId(crypto.randomUUID()); }}>
        <option value="">{translate("Chọn làn xe")}</option>
        {lanes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
      </Select>
      <Button loading={loading} disabled={!file || !lane} onClick={() => void run()}>{translate("Chạy nhận diện")}</Button>
      <Button loading={loading} disabled={!file || !lane || Boolean(result?.detection_id)} onClick={() => void run(true)}>{translate("Lưu kết quả")}</Button>
    </div>
    {file && preview && <DetectionImage key={preview} src={preview} bbox={bbox ? { x: bbox[0], y: bbox[1], w: bbox[2] - bbox[0], h: bbox[3] - bbox[1] } : null} />}
    {result && <div className="card">
      {result.detection_id && <p role="status">{translate("Đã lưu detection:")}{result.detection_id}</p>}
      <p>{translate("Biển số:")}{result.normalized_plate_number ?? translate("Không đọc được biển số")}</p>
      <pre className="code-block">{JSON.stringify(result, null, 2)}</pre>
    </div>}
  </section>
}
