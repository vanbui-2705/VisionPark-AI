import { useEffect, useState } from 'react'
import { healthApi } from '../../api/healthApi.ts'
import { getApiBaseUrl } from '../../api/client.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'

export function SystemPage() {
  const [data,setData]=useState<unknown>(null)
  const [err,setErr]=useState<string|null>(null)
  const [loading,setLoading]=useState(true)
  const load=async()=>{ setLoading(true); setErr(null); try{ const r=await healthApi.ready(); setData(r)}catch(e){ setErr(e instanceof Error?e.message:'Không kết nối được backend')} finally{ setLoading(false)}}
  useEffect(()=>{ void load()},[])
  return (
    <div>
      <h2>Trạng thái hệ thống</h2>
      <div className="stat-grid" style={{marginTop:12}}>
        <div className="stat-card"><div className="stat-label">Backend</div><div className="stat-value" style={{fontSize:16}}>{err?'● Error':'● Healthy'}</div></div>
        <div className="stat-card"><div className="stat-label">ALPR</div><div className="stat-value" style={{fontSize:16}}>{(data as {alpr?:{provider?:string}})?.alpr?.provider ?? '—'}</div></div>
        <div className="stat-card"><div className="stat-label">Frontend</div><div className="stat-value" style={{fontSize:16}}>● Running</div></div>
      </div>
      <section className="card" style={{marginTop:12}}>
        <ul className="kv">
          <li>API Base URL: {getApiBaseUrl()}</li>
          <li>Environment: {import.meta.env.MODE}</li>
        </ul>
        {loading ? <Spinner /> : err ? <Alert variant="error">{err}</Alert> : <pre className="code-block">{JSON.stringify(data,null,2)??'—'}</pre>}
        <Button onClick={load} style={{marginTop:8}}>Kiểm tra lại</Button>
      </section>
    </div>
  )
}
