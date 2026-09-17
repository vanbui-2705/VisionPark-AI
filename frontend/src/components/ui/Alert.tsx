export function Alert({ children, variant = 'error' }: { children: React.ReactNode; variant?: 'error' | 'info' | 'success' | 'warning' }) {
  return <div role="alert" data-variant={variant} className={`alert alert-${variant}`}>{children}</div>
}
