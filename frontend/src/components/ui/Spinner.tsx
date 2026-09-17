export function Spinner({ label = 'Đang tải...' }: { label?: string }) {
  return <div role="status" aria-label={label} className="spinner">{label}</div>
}
