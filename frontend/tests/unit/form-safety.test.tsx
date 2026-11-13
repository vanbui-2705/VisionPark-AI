import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Link, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Input } from '../../src/components/ui/Input.tsx'
import { Select } from '../../src/components/ui/Select.tsx'
import { useUnsavedGuard } from '../../src/hooks/useUnsavedGuard.ts'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

function GuardedForm() {
  useUnsavedGuard(true)
  const location = useLocation()
  return <><span>{location.pathname}</span><Link to="/next">Tiếp tục</Link></>
}

describe('form safety and accessibility', () => {
  it('associates generated field ids and errors with their controls', () => {
    render(<><Input label="Biển số" error="Bắt buộc" /><Select label="Loại xe" error="Bắt buộc"><option>Ô tô</option></Select></>)
    const input = screen.getByLabelText('Biển số')
    const select = screen.getByLabelText('Loại xe')
    expect(input.id).not.toBe('')
    expect(select.id).not.toBe('')
    expect(input).toHaveAttribute('aria-describedby', `${input.id}-error`)
    expect(select).toHaveAttribute('aria-describedby', `${select.id}-error`)
  })

  it('blocks internal link navigation when the user cancels with unsaved changes', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<MemoryRouter initialEntries={['/form']}><GuardedForm /></MemoryRouter>)
    await userEvent.click(screen.getByRole('link', { name: 'Tiếp tục' }))
    expect(screen.getByText('/form')).toBeInTheDocument()
    expect(window.confirm).toHaveBeenCalledOnce()
  })

  it('allows internal link navigation after confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<MemoryRouter initialEntries={['/form']}><GuardedForm /></MemoryRouter>)
    await userEvent.click(screen.getByRole('link', { name: 'Tiếp tục' }))
    expect(screen.getByText('/next')).toBeInTheDocument()
  })
})
