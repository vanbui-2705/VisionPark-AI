import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { Alert } from '../../components/ui/Alert.tsx'

type Product = { id: string; code: string; name: string; kind: string; vehicle_type: string; active: boolean }
type Vehicle = { id: string; normalized_plate: string | null; ticket_code: string | null; vehicle_type: string; customer_class_id: string | null }
type Subscription = { id: string; product_id: string; vehicle_id: string; zone_id: string; valid_from: string; valid_until: string; grace_days: number }

const localIso = (value: string) => new Date(value).toISOString()
const fmt = (value: string) => new Date(value).toLocaleString('vi-VN')
const localInput = (value: Date) => {
  const pad = (number: number) => String(number).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`
}

export function MonthlyTickets() {
  const [products, setProducts] = useState<Product[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [productId, setProductId] = useState('')
  const [plate, setPlate] = useState('')
  const [vehicleType, setVehicleType] = useState('MOTORBIKE')
  const [customerClassId, setCustomerClassId] = useState('')
  const [zoneId, setZoneId] = useState('')
  const [validFrom, setValidFrom] = useState(localInput(new Date()))
  const [validUntil, setValidUntil] = useState(localInput(new Date(new Date().setMonth(new Date().getMonth() + 1))))
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    const [nextProducts, nextVehicles, nextSubscriptions] = await Promise.all([
      apiClient.get<Product[]>('/api/v1/pricing/ticket-products'),
      apiClient.get<Vehicle[]>('/api/v1/tickets/vehicles'),
      apiClient.get<Subscription[]>('/api/v1/tickets/subscriptions'),
    ])
    setProducts(nextProducts.filter(item => item.active && item.kind === 'MONTHLY'))
    setVehicles(nextVehicles)
    setSubscriptions(nextSubscriptions)
    if (!productId) setProductId(nextProducts.find(item => item.active && item.kind === 'MONTHLY')?.id ?? '')
  }
  useEffect(() => { void refresh().catch(e => setError(e instanceof Error ? e.message : 'Không tải được vé tháng.')) }, [])

  const activeSubByVehicle = useMemo(() => {
    const latest = new Map<string, Subscription>()
    subscriptions.forEach(sub => {
      const current = latest.get(sub.vehicle_id)
      if (!current || new Date(sub.valid_until) > new Date(current.valid_until)) latest.set(sub.vehicle_id, sub)
    })
    return latest
  }, [subscriptions])

  async function submit(action: () => Promise<unknown>, success: string) {
    setBusy(true); setError(''); setNotice('')
    try { await action(); await refresh(); setNotice(success) }
    catch (e) { setError(e instanceof Error ? e.message : 'Thao tác thất bại.') }
    finally { setBusy(false) }
  }

  async function registerOrRenew() {
    if (!productId || !zoneId || !validUntil) { setError('Chọn gói vé tháng, mã khu vực và ngày hết hạn.'); return }
    await submit(async () => {
      let vehicle = vehicles.find(item => item.normalized_plate === plate.trim().toUpperCase().replace(/[^A-Z0-9]/g, ''))
      if (!vehicle) vehicle = await apiClient.post<Vehicle>('/api/v1/tickets/vehicles', {
        normalized_plate: plate, vehicle_type: vehicleType, customer_class_id: customerClassId || null,
      })
      const previous = activeSubByVehicle.get(vehicle.id)
      const start = previous && new Date(previous.valid_until) > new Date(validFrom)
        ? new Date(previous.valid_until).toISOString()
        : localIso(validFrom)
      await apiClient.post('/api/v1/tickets/subscriptions', {
        product_id: productId, vehicle_id: vehicle.id, zone_id: zoneId,
        valid_from: start, valid_until: localIso(validUntil), grace_days: 3,
      })
    }, 'Đã đăng ký/gia hạn vé tháng.')
  }

  async function importCsv() {
    if (!file) { setError('Chọn tệp CSV cần nhập.'); return }
    const form = new FormData(); form.append('file', file)
    await submit(async () => {
      const result = await apiClient.postMultipart<{ imported: number }>('/api/v1/tickets/vehicles/import', form)
      setNotice(`Đã nhập ${result.imported} xe từ CSV.`)
    }, 'Đã nhập CSV.')
  }

  return <section className="card card-polished stack">
    <div className="card-head"><div><span className="card-kicker">RESIDENT MONTHLY PASSES</span><h2>Quản lý xe vé tháng</h2></div></div>
    <p className="muted">Đăng ký theo biển số; gia hạn nối tiếp ngày hết hạn hiện tại. CSV dùng cột <code>normalized_plate,vehicle_type,customer_class_id</code>.</p>
    {error && <Alert variant="error">{error}</Alert>}{notice && <Alert variant="success">{notice}</Alert>}
    <form className="stack" onSubmit={e => { e.preventDefault(); void registerOrRenew() }}>
      <div className="form-grid">
        <label className="field"><span>Biển số xe</span><input required value={plate} onChange={e => setPlate(e.target.value)} placeholder="Ví dụ: 30A12345" /></label>
        <label className="field"><span>Loại xe</span><select value={vehicleType} onChange={e => setVehicleType(e.target.value)}><option value="CAR">Ô tô</option><option value="MOTORBIKE">Xe máy</option><option value="BICYCLE">Xe đạp</option></select></label>
        <label className="field"><span>Gói vé tháng</span><select required value={productId} onChange={e => setProductId(e.target.value)}><option value="">Chọn gói</option>{products.map(item => <option key={item.id} value={item.id}>{item.name} ({item.vehicle_type})</option>)}</select></label>
        <label className="field"><span>Mã hạng khách (UUID, nếu có)</span><input value={customerClassId} onChange={e => setCustomerClassId(e.target.value)} /></label>
        <label className="field"><span>Mã khu vực (UUID)</span><input required value={zoneId} onChange={e => setZoneId(e.target.value)} /></label>
        <label className="field"><span>Bắt đầu từ</span><input required type="datetime-local" value={validFrom} onChange={e => setValidFrom(e.target.value)} /></label>
        <label className="field"><span>Hết hạn</span><input required type="datetime-local" value={validUntil} onChange={e => setValidUntil(e.target.value)} /></label>
      </div>
      <div><button className="btn btn-primary" disabled={busy || !productId}>Đăng ký / gia hạn</button></div>
    </form>
    <form className="row-actions" onSubmit={e => { e.preventDefault(); void importCsv() }}>
      <label className="field"><span>Nhập danh sách xe CSV</span><input type="file" accept=".csv,text/csv" onChange={e => setFile(e.target.files?.[0] ?? null)} /></label>
      <button className="btn" disabled={busy || !file}>Nhập CSV</button>
    </form>
    <div><h3>Xe đã đăng ký ({vehicles.length})</h3>
      <div className="table-wrap"><table><thead><tr><th>Biển số / mã vé</th><th>Loại xe</th><th>Hạn vé tháng gần nhất</th><th>Trạng thái</th></tr></thead><tbody>
        {vehicles.map(vehicle => { const sub = activeSubByVehicle.get(vehicle.id); const valid = sub && new Date(sub.valid_until) >= new Date(); return <tr key={vehicle.id}><td>{vehicle.normalized_plate ?? vehicle.ticket_code ?? '—'}</td><td>{vehicle.vehicle_type}</td><td>{sub ? fmt(sub.valid_until) : 'Chưa có'}</td><td>{valid ? 'Còn hạn' : sub ? 'Hết hạn' : 'Chưa đăng ký'}</td></tr> })}
      </tbody></table></div>
    </div>
  </section>
}
