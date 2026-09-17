import { BrowserRouter } from 'react-router-dom'
import { AppRoutes } from './app/router.tsx'
import { AuthProvider } from './modules/auth/AuthContext.tsx'
import { AppErrorBoundary } from './components/AppErrorBoundary.tsx'
import { ToastProvider } from './components/ui/Toast.tsx'

export default function App() {
  return (
    <AppErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </AppErrorBoundary>
  )
}
