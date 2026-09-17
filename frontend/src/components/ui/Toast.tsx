import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'
export type Toast = { id: number; message: string; variant: ToastVariant }

const Ctx = createContext<{
  toasts: Toast[]
  push: (message: string, variant?: ToastVariant) => void
  dismiss: (id: number) => void
} | null>(null)

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = nextId++
    setToasts((t) => [...t, { id, message, variant }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500)
  }, [])
  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  return (
    <Ctx.Provider value={{ toasts, push, dismiss }}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.variant}`}>
            {t.message}
            <button type="button" className="toast-close" aria-label="Close" onClick={() => dismiss(t.id)}>×</button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}

const NOOP = { toasts: [] as Toast[], push: () => {}, dismiss: () => {} }

export function useToast() {
  // App luôn mount ToastProvider; fallback no-op chỉ để test render độc lập.
  return useContext(Ctx) ?? NOOP
}
