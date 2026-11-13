import { useEffect, type RefObject } from 'react'

const actions: Record<string, string> = { F2: 'capture', F4: 'confirm', F8: 'cash', F9: 'next', F10: 'gate' }

export function useStationShortcuts(root: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.repeat || event.isComposing || event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return
      const target = event.target
      if (target instanceof HTMLElement && (target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"]') || target.closest('dialog[open], [role="dialog"], [role="alertdialog"]'))) return
      const action = actions[event.key]
      if (!action || document.querySelector('dialog[open], [role="dialog"][aria-modal="true"], [role="alertdialog"][aria-modal="true"]')) return
      const button = root.current?.querySelector<HTMLButtonElement>(`button[data-station-shortcut="${action}"]:not(:disabled)`)
      if (!button) return
      event.preventDefault()
      button.click()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [root])
}
