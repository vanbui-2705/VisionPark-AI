import { useEffect, useRef } from 'react'

export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onCancel = (e: Event) => {
      e.preventDefault()
      onClose()
    }
    el.addEventListener('cancel', onCancel)
    return () => el.removeEventListener('cancel', onCancel)
  }, [onClose])
  return (
    <dialog ref={ref} onClose={onClose} aria-label={title} className="dialog">
      <div className="dialog-header">
        <h3>{title}</h3>
        <button type="button" onClick={onClose} aria-label="Close">×</button>
      </div>
      <div className="dialog-body">{children}</div>
    </dialog>
  )
}
