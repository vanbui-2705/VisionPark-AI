export function Badge({ children, variant = 'neutral' }: { children: React.ReactNode; variant?: 'neutral'|'success'|'warning'|'danger'|'info' }) {
  return <span className={`badge badge-${variant}`}>{children}</span>
}
