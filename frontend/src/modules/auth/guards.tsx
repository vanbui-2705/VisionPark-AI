import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.tsx'

export function ProtectedRoute({ children }: { children?: React.ReactNode }) {
  const { initialized, isAuthenticated } = useAuth()
  const loc = useLocation()
  if (!initialized) return <div style={{ padding: 24 }}>Đang tải...</div>
  if (!isAuthenticated) {
    const returnUrl = loc.pathname + loc.search
    return <Navigate to={`/login?returnUrl=${encodeURIComponent(returnUrl)}`} replace />
  }
  return children ? <>{children}</> : <Outlet />
}

export function RoleGuard({
  allow,
  children,
  fallback,
}: {
  allow: boolean
  children?: React.ReactNode
  fallback?: React.ReactNode
}) {
  if (!allow) {
    if (fallback) return <>{fallback}</>
    return <Navigate to="/station" replace />
  }
  return children ? <>{children}</> : <Outlet />
}
