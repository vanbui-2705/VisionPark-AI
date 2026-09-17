import { useEffect, useState } from 'react'
import { healthApi } from '../../api/healthApi.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'

export function AlprPage() {
  const [data, setData] = useState<unknown>(null)
  const [err, setErr] = useState<string|null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(()=>{ healthApi.ready().then(setData).catch(e=> setErr(e instanceof Error?e.message:'Không tải được ALPR status')).finally(()=> setLoading(false)) }, [])
  if (loading) return <Spinner />
  if (err) return <Alert variant="error">{err}</Alert>
  const alpr = (data as {alpr?:{provider?:string; ready?:boolean; model_version?:string; runtime?:string; confidence_threshold?:number}})?.alpr
  const isMock = (alpr?.provider ?? '').toLowerCase().includes('mock')
  return (
    <div>
      <h2>ALPR</h2>
      {isMock ? <Alert variant="warning">⚠ HỆ THỐNG ĐANG CHẠY MOCK PROVIDER — Kết quả không từ model AI thực tế.</Alert>:null}
      <section className="card">
        <ul className="kv">
          <li>Provider: {alpr?.provider ?? '—'}</li>
          <li>Ready: {String(alpr?.ready ?? '—')}</li>
          <li>Model Version: {alpr?.model_version ?? '—'}</li>
          <li>Runtime: {alpr?.runtime ?? '—'}</li>
          <li>Confidence Threshold: {String(alpr?.confidence_threshold ?? '0.85')}</li>
        </ul>
        <pre className="code-block">{JSON.stringify(data,null,2)}</pre>
        <p className="muted">Chỉ readonly — không chỉnh config khi backend chưa có API.</p>
      </section>
    </div>
  )
}
