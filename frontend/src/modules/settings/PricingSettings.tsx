import { useEffect, useState } from 'react'
import { apiClient } from '../../api/client.ts'
import { Alert } from '../../components/ui/Alert.tsx'

type CustomerClass = { id: string; code: string; name: string; discount_percent: number; active: boolean }
type Product = { id: string; code: string; name: string; kind: string; vehicle_type: string; active: boolean }
type Quota = { id: string; customer_class_id: string; vehicle_type: string; max_active: number }
type PriceRule = { vehicle_type: string; ticket_kind: string; customer_class: string; free_minutes: number; initial_minutes: number; initial_fee: number; block_minutes: number; block_fee: number; daily_cap: number | null; overnight_fee: number; lost_ticket_fee: number; overtime_fee: number; day_pass_fee: number; month_pass_fee: number; windows: { start_minute: number; end_minute: number }[] }
type Version = { id: string; version_number: number; active_from: string; rules: PriceRule[] }
type FeePreview = { total: number; currency: string; lines: { code: string; amount: number; quantity: number }[] }
type Tab = 'products' | 'pricing' | 'classes'

export function PricingSettings() {
  const [tab, setTab] = useState<Tab>('products')
  const [classes, setClasses] = useState<CustomerClass[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [versions, setVersions] = useState<Version[]>([])
  const [quotas, setQuotas] = useState<Quota[]>([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [classCode, setClassCode] = useState('')
  const [className, setClassName] = useState('')
  const [discount, setDiscount] = useState(0)
  const [maxActive, setMaxActive] = useState(0)
  const [productCode, setProductCode] = useState('')
  const [productName, setProductName] = useState('')
  const [kind, setKind] = useState('HOURLY')
  const [vehicleType, setVehicleType] = useState('CAR')
  const [classId, setClassId] = useState('')
  const [initialFee, setInitialFee] = useState(0)
  const [blockFee, setBlockFee] = useState(0)
  const [dailyCap, setDailyCap] = useState('')
  const [overnightFee, setOvernightFee] = useState(0)
  const [lostTicketFee, setLostTicketFee] = useState(0)
  const [overtimeFee, setOvertimeFee] = useState(0)
  const [dayPassFee, setDayPassFee] = useState(0)
  const [monthPassFee, setMonthPassFee] = useState(0)
  const [previewStart, setPreviewStart] = useState('')
  const [previewEnd, setPreviewEnd] = useState('')
  const [feePreview, setFeePreview] = useState<FeePreview | null>(null)
  const [freeMinutes, setFreeMinutes] = useState(0)
  const [initialMinutes, setInitialMinutes] = useState(60)
  const [blockMinutes, setBlockMinutes] = useState(60)

  async function refresh() {
    const [nextClasses, nextProducts, nextVersions, nextQuotas] = await Promise.all([
      apiClient.get<CustomerClass[]>('/api/v1/pricing/customer-classes'),
      apiClient.get<Product[]>('/api/v1/pricing/ticket-products'),
      apiClient.get<Version[]>('/api/v1/pricing/versions'),
      apiClient.get<Quota[]>('/api/v1/tickets/quotas'),
    ])
    setClasses(nextClasses); setProducts(nextProducts); setVersions(nextVersions)
    setQuotas(nextQuotas)
    if (!classId && nextClasses.length) setClassId(nextClasses[0].id)
  }
  useEffect(() => { void refresh().catch(e => setError(e instanceof Error ? e.message : 'Không tải được dữ liệu.')) }, [])

  async function save(action: () => Promise<unknown>) {
    setBusy(true); setError(''); setMessage('')
    try { await action(); await refresh(); setMessage('Đã lưu.') }
    catch (e) { setError(e instanceof Error ? e.message : 'Lưu thất bại.') }
    finally { setBusy(false) }
  }

  function saveVersion() {
    const selected = classes.find(item => item.id === classId)
    const previous = versions[0]?.rules.flatMap(rule => {
      const previousClass = classes.find(item => item.code === rule.customer_class)
      if (!previousClass || (rule.vehicle_type === vehicleType && rule.ticket_kind === kind && previousClass.id === classId)) return []
      return [{ ...rule, customer_class_id: previousClass.id }]
    }) ?? []
    if (!selected) { setError('Chọn hạng khách trước khi lưu.'); return }
    const rule = { vehicle_type: vehicleType, ticket_kind: kind, customer_class_id: classId, free_minutes: freeMinutes, initial_minutes: initialMinutes, initial_fee: initialFee, block_minutes: blockMinutes, block_fee: blockFee, daily_cap: dailyCap === '' ? null : Number(dailyCap), overnight_fee: overnightFee, lost_ticket_fee: lostTicketFee, overtime_fee: overtimeFee, day_pass_fee: dayPassFee, month_pass_fee: monthPassFee }
    void save(() => apiClient.post('/api/v1/pricing/versions', { active_from: new Date().toISOString(), rules: [...previous, rule] }))
  }

  return <section className="card">
    <h2>Cấu hình vé và giá</h2>
    <div role="tablist" style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
      <button type="button" role="tab" aria-selected={tab === 'products'} className="btn" onClick={() => setTab('products')}>Loại vé</button>
      <button type="button" role="tab" aria-selected={tab === 'pricing'} className="btn" onClick={() => setTab('pricing')}>Bảng giá</button>
      <button type="button" role="tab" aria-selected={tab === 'classes'} className="btn" onClick={() => setTab('classes')}>Hạng khách</button>
    </div>
    {error && <Alert variant="error">{error}</Alert>}{message && <Alert variant="success">{message}</Alert>}
    {tab === 'classes' && <div>
      <form onSubmit={e => { e.preventDefault(); void save(() => apiClient.post('/api/v1/pricing/customer-classes', { code: classCode, name: className, discount_percent: discount })) }}>
        <label>Mã hạng<input required maxLength={40} value={classCode} onChange={e => setClassCode(e.target.value)} /></label>
        <label>Tên hạng<input required maxLength={120} value={className} onChange={e => setClassName(e.target.value)} /></label>
        <label>Giảm giá (%)<input required type="number" min="0" max="100" value={discount} onChange={e => setDiscount(Number(e.target.value))} /></label>
        <button className="btn btn-primary" disabled={busy}>Tạo hạng khách</button>
      </form>
      <ul>{classes.map(item => <li key={item.id}>{item.code} — {item.name} — {item.discount_percent}%</li>)}</ul>
      <form onSubmit={e => { e.preventDefault(); void save(() => apiClient.put('/api/v1/tickets/quotas', { customer_class_id: classId, vehicle_type: vehicleType, max_active: maxActive })) }}>
        <h3>Hạn mức hạng khách</h3>
        <label>Hạng khách<select value={classId} onChange={e => setClassId(e.target.value)}>{classes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Loại xe<input required value={vehicleType} onChange={e => setVehicleType(e.target.value)} /></label>
        <label>Số xe tối đa<input type="number" min="0" value={maxActive} onChange={e => setMaxActive(Number(e.target.value))} /></label>
        <button className="btn btn-primary" disabled={busy || !classId}>Lưu hạn mức</button>
      </form>
      <ul>{quotas.map(item => <li key={item.id}>{classes.find(c => c.id === item.customer_class_id)?.name ?? item.customer_class_id} / {item.vehicle_type}: {item.max_active}</li>)}</ul>
    </div>}
    {tab === 'products' && <div>
      <form onSubmit={e => { e.preventDefault(); void save(() => apiClient.post('/api/v1/pricing/ticket-products', { code: productCode, name: productName, kind, vehicle_type: vehicleType })) }}>
        <label>Mã vé<input required maxLength={40} value={productCode} onChange={e => setProductCode(e.target.value)} /></label>
        <label>Tên vé<input required maxLength={120} value={productName} onChange={e => setProductName(e.target.value)} /></label>
        <label>Loại<select value={kind} onChange={e => setKind(e.target.value)}><option value="HOURLY">Theo giờ</option><option value="DAILY">Ngày</option><option value="MONTHLY">Tháng</option><option value="NIGHT">Đêm</option></select></label>
        <label>Loại xe<input required value={vehicleType} onChange={e => setVehicleType(e.target.value)} /></label>
        <button className="btn btn-primary" disabled={busy}>Tạo loại vé</button>
      </form>
      <ul>{products.map(item => <li key={item.id}>{item.code} — {item.name} — {item.kind} / {item.vehicle_type}</li>)}</ul>
    </div>}
    {tab === 'pricing' && <div>
      <p>Mỗi lần lưu tạo một phiên bản giá mới. Phiên bản đã có không bị sửa.</p>
      <form onSubmit={e => { e.preventDefault(); saveVersion() }}>
        <label>Loại xe<input required value={vehicleType} onChange={e => setVehicleType(e.target.value)} /></label>
        <label>Loại vé<select value={kind} onChange={e => setKind(e.target.value)}><option value="HOURLY">Theo giờ</option><option value="DAILY">Ngày</option><option value="MONTHLY">Tháng</option><option value="NIGHT">Đêm</option></select></label>
        <label>Hạng khách<select required value={classId} onChange={e => setClassId(e.target.value)}>{classes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Miễn phí (phút)<input type="number" min="0" value={freeMinutes} onChange={e => setFreeMinutes(Number(e.target.value))} /></label>
        <label>Khối đầu (phút)<input type="number" min="1" value={initialMinutes} onChange={e => setInitialMinutes(Number(e.target.value))} /></label>
        <label>Giá khối đầu (VND)<input type="number" min="0" value={initialFee} onChange={e => setInitialFee(Number(e.target.value))} /></label>
        <label>Khối tiếp theo (phút)<input type="number" min="1" value={blockMinutes} onChange={e => setBlockMinutes(Number(e.target.value))} /></label>
        <label>Giá khối tiếp theo (VND)<input type="number" min="0" value={blockFee} onChange={e => setBlockFee(Number(e.target.value))} /></label>
        <label>Trần ngày (VND)<input type="number" min="0" value={dailyCap} onChange={e => setDailyCap(e.target.value)} /></label>
        <label>Phí qua đêm (VND)<input type="number" min="0" value={overnightFee} onChange={e => setOvernightFee(Number(e.target.value))} /></label>
        <label>Phí mất vé (VND)<input type="number" min="0" value={lostTicketFee} onChange={e => setLostTicketFee(Number(e.target.value))} /></label>
        <label>Phí quá giờ (VND)<input type="number" min="0" value={overtimeFee} onChange={e => setOvertimeFee(Number(e.target.value))} /></label>
        <label>Giá vé ngày (VND)<input type="number" min="0" value={dayPassFee} onChange={e => setDayPassFee(Number(e.target.value))} /></label>
        <label>Giá vé tháng (VND)<input type="number" min="0" value={monthPassFee} onChange={e => setMonthPassFee(Number(e.target.value))} /></label>
        <button className="btn btn-primary" disabled={busy || !classId}>Tạo phiên bản giá</button>
      </form>
      <ul>{versions.map(item => <li key={item.id}>Phiên bản {item.version_number} — {new Date(item.active_from).toLocaleString()} — {item.rules.length} quy tắc</li>)}</ul>
      <h3>Xem trước phí theo bảng giá đang hiệu lực</h3>
      <label>Giờ vào<input type="datetime-local" value={previewStart} onChange={e => setPreviewStart(e.target.value)} /></label>
      <label>Giờ ra<input type="datetime-local" value={previewEnd} onChange={e => setPreviewEnd(e.target.value)} /></label>
      <button type="button" className="btn" disabled={busy || !classId || !previewStart || !previewEnd} onClick={() => {
        setError(''); setFeePreview(null)
        void apiClient.post<FeePreview>('/api/v1/pricing/preview', { vehicle_type: vehicleType, ticket_kind: kind, customer_class_id: classId, check_in: new Date(previewStart).toISOString(), check_out: new Date(previewEnd).toISOString() })
          .then(setFeePreview).catch(e => setError(e instanceof Error ? e.message : 'Không tính được phí.'))
      }}>Tính thử</button>
      {feePreview && <div role="status"><strong>Tổng: {feePreview.total.toLocaleString('vi-VN')} {feePreview.currency}</strong><ul>{feePreview.lines.map((line, index) => <li key={`${line.code}-${index}`}>{line.code}: {line.amount.toLocaleString('vi-VN')}</li>)}</ul></div>}
    </div>}
  </section>
}
