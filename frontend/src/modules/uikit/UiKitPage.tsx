import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Table } from '../../components/ui/Table.tsx'
import { Dialog } from '../../components/ui/Dialog.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { useToast } from '../../components/ui/Toast.tsx'
import { useState } from 'react'

export function UiKitPage() {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  return (
    <div>
      <Breadcrumb items={[{ label: 'UI Kit' }]} />
      <h2>/dev/ui-kit</h2>
      <p className="muted">Thư viện component dùng chung — kiểm tra visual bằng mắt, không phụ thuộc backend.</p>

      <section className="card"><h3>Buttons</h3><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><Button>Default</Button><Button variant="primary">Primary</Button><Button variant="danger">Danger</Button><Button variant="secondary">Secondary</Button><Button disabled>Disabled</Button><Button loading>Loading</Button></div></section>
      <section className="card" style={{ marginTop: 12 }}><h3>Inputs</h3><div style={{ display: 'grid', gap: 8, maxWidth: 420 }}><Input label="Text" placeholder="hello" /><Input label="With error" error="Bắt buộc" /><Select label="Select"><option>IN</option><option>OUT</option></Select></div></section>
      <section className="card" style={{ marginTop: 12 }}><h3>Alert / Badge / Spinner / Skeleton / Empty</h3><div style={{ display: 'grid', gap: 8 }}><Alert variant="info">Info alert</Alert><Alert variant="error">Error alert</Alert><Alert variant="success">Success alert</Alert><div style={{ display: 'flex', gap: 6 }}><Badge>neutral</Badge><Badge variant="success">success</Badge><Badge variant="warning">warning</Badge><Badge variant="danger">danger</Badge><Badge variant="info">info</Badge></div><Spinner label="Loading..." /><Skeleton lines={3} /><EmptyState title="Trống" description="Mô tả trống." /></div></section>
      <section className="card" style={{ marginTop: 12 }}><h3>Table</h3><Table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></Table></section>
      <section className="card" style={{ marginTop: 12 }}><h3>Dialog / Toast / Breadcrumb</h3><Breadcrumb items={[{ label: 'Home', to: '/' }, { label: 'Current' }]} /><div style={{ display: 'flex', gap: 8, marginTop: 8 }}><Button onClick={() => setOpen(true)}>Open dialog</Button><Button onClick={() => toast.push('Hello toast', 'success')}>Push toast</Button><Button onClick={() => toast.push('Error toast', 'error')}>Error toast</Button></div><Dialog open={open} onClose={() => setOpen(false)} title="Dialog mẫu"><p>Nội dung dialog.</p></Dialog></section>
    </div>
  )
}
