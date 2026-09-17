import { useEffect } from 'react'

export function useUnsavedGuard(dirty: boolean, message = 'Bạn có thay đổi chưa lưu. Bạn có chắc muốn rời khỏi trang?'): void {
  useEffect(() => {
    if (!dirty) return
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = message
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [dirty, message])
}
