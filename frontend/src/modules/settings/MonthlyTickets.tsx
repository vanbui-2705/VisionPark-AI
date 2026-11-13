import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { Alert } from '../../components/ui/Alert.tsx'

type Product = { id: string; code: string; name: string; kind: string; vehicle_type: string; customer_class_id: string | null; active: boolean }
type Vehicle = { id: string; normalized_plate: string | null; ticket_code: string | null; vehicle_type: string; customer_class_id: string | null }
type Subscription = { id: string; product_id: string; vehicle_id: string; zone_id: string; valid_from: string; valid_until: string; grace_days: number }
type CustomerClass = { id: string; code: string; name: string; active: boolean }
type ParkingZone = { id: string; code: string; name: string; active: boolean }

const fmt = (value: string) => new Date(value).toLocaleString('vi-VN')
const normalizePlate = (value: string) => value.trim().toUpperCase().replace(/[^A-Z0-9]/g, '')
const normalizeCode = (value: string) => value.trim().toUpperCase()
const localInput = (value: Date) => {
  const pad = (number: number) => String(number).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`
}

export function MonthlyTickets() {
  const [products, setProducts] = useState<Product[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [classes, setClasses] = useState<CustomerClass[]>([])
  const [zones, setZones] = useState<ParkingZone[]>([])
  const [productId, setProductId] = useState('')
  const [identifier, setIdentifier] = useState('')
  const [vehicleType, setVehicleType] = useState('MOTORBIKE')
  const [customerClassId, setCustomerClassId] = useState('')
  const [zoneId, setZoneId] = useState('')
  const [zoneCode, setZoneCode] = useState('')
  const [zoneName, setZoneName] = useState('')
  const [validFrom, setValidFrom] = useState(localInput(new Date()))
  const [validUntil, setValidUntil] = useState(localInput(new Date(new Date().setMonth(new Date().getMonth() + 1))))
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    const [nextProducts, nextVehicles, nextSubscriptions, nextClasses, nextZones] = await Promise.all([
      apiClient.get<Product[]>('/api/v1/pricing/ticket-products'),
      apiClient.get<Vehicle[]>('/api/v1/tickets/vehicles'),
      apiClient.get<Subscription[]>('/api/v1/tickets/subscriptions'),
      apiClient.get<CustomerClass[]>('/api/v1/pricing/customer-classes'),
      apiClient.get<ParkingZone[]>('/api/v1/tickets/zones'),
    ])
    setProducts(nextProducts.filter(item => item.active && item.kind === 'MONTHLY'))
    setVehicles(nextVehicles)
    setSubscriptions(nextSubscriptions)
    setClasses(nextClasses.filter(item => item.active))
    setZones(nextZones.filter(item => item.active))
    setCustomerClassId(current => current || nextClasses.find(item => item.active)?.id || '')
    setZoneId(current => current || nextZones.find(item => item.active)?.id || '')
  }

  useEffect(() => { void refresh().catch(e => setError(e instanceof Error ? e.message : 'Không tải được vé tháng.')) }, [])

  const filteredProducts = useMemo(
    () => products.filter(item => item.vehicle_type === vehicleType && (!item.customer_class_id || item.customer_class_id === customerClassId)),
    [products, vehicleType, customerClassId],
  )

  useEffect(() => {
    if (!filteredProducts.some(item => item.id === productId)) setProductId(filteredProducts[0]?.id ?? '')
  }, [filteredProducts, productId])

  const activeSubByVehicle = useMemo(() => {
    const latest = new Map<string, Subscription>()
    subscriptions.forEach(sub => {
      const current = latest.get(sub.vehicle_id)
      if (!current || new Date(sub.valid_until) > new Date(current.valid_until)) latest.set(sub.vehicle_id, sub)
    })
    return latest
  }, [subscriptions])

  const activeSubByVehicleZone = useMemo(() => {
    const latest = new Map<string, Subscription>()
    subscriptions.forEach(sub => {
      const key = `${sub.vehicle_id}:${sub.zone_id}`
      const current = latest.get(key)
      if (!current || new Date(sub.valid_until) > new Date(current.valid_until)) latest.set(key, sub)
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
    if (!productId || !zoneId || !validUntil || !identifier.trim()) {
      setError('Nhập mã xe và chọn đầy đủ gói vé, khu vực, ngày hết hạn.')
      return
    }
    await submit(async () => {
      const isBicycle = vehicleType === 'BICYCLE'
      const normalized = isBicycle ? normalizeCode(identifier) : normalizePlate(identifier)
      let vehicle = vehicles.find(item => isBicycle
        ? item.ticket_code === normalized
        : item.normalized_plate === normalized)
      if (vehicle && vehicle.vehicle_type !== vehicleType) throw new Error('Mã xe đã tồn tại với loại xe khác.')
      if (vehicle && customerClassId && vehicle.customer_class_id !== customerClassId) throw new Error('Xe đã tồn tại với hạng khách hàng khác.')
      if (!vehicle) vehicle = await apiClient.post<Vehicle>('/api/v1/tickets/vehicles', {
        normalized_plate: isBicycle ? null : normalized,
        ticket_code: isBicycle ? normalized : null,
        vehicle_type: vehicleType,
        customer_class_id: customerClassId || null,
      })
      const previous = activeSubByVehicleZone.get(`${vehicle.id}:${zoneId}`)
      const requestedStart = new Date(validFrom)
      const previousEnd = previous ? new Date(previous.valid_until) : null
      const start = previousEnd && previousEnd >= requestedStart
        ? new Date(previousEnd.getTime() + 1)
        : requestedStart
      let end = new Date(validUntil)
      if (end <= start) {
        end = new Date(start)
        end.setMonth(end.getMonth() + 1)
      }
      await apiClient.post('/api/v1/tickets/subscriptions', {
        product_id: productId,
        vehicle_id: vehicle.id,
        zone_id: zoneId,
        valid_from: start.toISOString(),
        valid_until: end.toISOString(),
        grace_days: 3,
      })
    }, 'Đã đăng ký/gia hạn vé tháng.')
  }

  async function createZone() {
    if (!zoneCode.trim() || !zoneName.trim()) { setError('Nhập mã và tên khu vực.'); return }
    await submit(async () => {
      const created = await apiClient.post<ParkingZone>('/api/v1/tickets/zones', { code: zoneCode, name: zoneName })
      setZoneId(created.id); setZoneCode(''); setZoneName('')
    }, 'Đã tạo khu vực đỗ xe.')
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
    <p className="muted">Đăng ký theo biển số hoặc mã vé xe đạp; lần gia hạn bắt đầu ngay sau khi gói hiện tại kết thúc. CSV dùng cột <code>normalized_plate,vehicle_type,customer_class_id</code>.</p>
    {error && <Alert variant="error">{error}</Alert>}{notice && <Alert variant="success">{notice}</Alert>}
    <form className="stack" onSubmit={e => { e.preventDefault(); void registerOrRenew() }}>
      <div className="form-grid">
        <label className="field"><span>{vehicleType === 'BICYCLE' ? 'Mã vé xe đạp' : 'Biển số xe'}</span><input required value={identifier} onChange={e => setIdentifier(e.target.value)} placeholder={vehicleType === 'BICYCLE' ? 'Ví dụ: BIKE-001' : 'Ví dụ: 30A12345'} /></label>
        <label className="field"><span>Loại xe</span><select value={vehicleType} onChange={e => setVehicleType(e.target.value)}><option value="CAR">Ô tô</option><option value="MOTORBIKE">Xe máy</option><option value="BICYCLE">Xe đạp</option></select></label>
        <label className="field"><span>Gói vé tháng</span><select required value={productId} onChange={e => setProductId(e.target.value)}><option value="">Chọn gói</option>{filteredProducts.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="field"><span>Hạng khách hàng</span><select value={customerClassId} onChange={e => setCustomerClassId(e.target.value)}><option value="">Không áp dụng</option>{classes.map(item => <option key={item.id} value={item.id}>{item.name} ({item.code})</option>)}</select></label>
        <label className="field"><span>Khu vực đỗ xe</span><select required value={zoneId} onChange={e => setZoneId(e.target.value)}><option value="">Chọn khu vực</option>{zones.map(item => <option key={item.id} value={item.id}>{item.name} ({item.code})</option>)}</select></label>
        <label className="field"><span>Bắt đầu từ</span><input required type="datetime-local" value={validFrom} onChange={e => setValidFrom(e.target.value)} /></label>
        <label className="field"><span>Hết hạn</span><input required type="datetime-local" value={validUntil} onChange={e => setValidUntil(e.target.value)} /></label>
      </div>
      <div><button className="btn btn-primary" disabled={busy || !productId || !zoneId}>Đăng ký / gia hạn</button></div>
    </form>
    <form className="row-actions" onSubmit={e => { e.preventDefault(); void createZone() }}>
      <label className="field"><span>Mã khu vực</span><input maxLength={40} value={zoneCode} onChange={e => setZoneCode(e.target.value)} placeholder="ZONE-A" /></label>
      <label className="field"><span>Tên khu vực</span><input maxLength={120} value={zoneName} onChange={e => setZoneName(e.target.value)} placeholder="Tầng hầm A" /></label>
      <button className="btn" disabled={busy || !zoneCode.trim() || !zoneName.trim()}>Thêm khu vực</button>
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
