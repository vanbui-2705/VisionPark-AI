import { BrowserRouter } from 'react-router-dom'
import { AppRoutes } from './app/router.tsx'
import { AuthProvider } from './modules/auth/AuthContext.tsx'
import { AppErrorBoundary } from './components/AppErrorBoundary.tsx'
import { ToastProvider } from './components/ui/Toast.tsx'
import { useLanguage } from './lib/i18n'

export default function App() {
  const language = useLanguage()
  return (
    <AppErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AppRoutes key={language} />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </AppErrorBoundary>
  )
}
