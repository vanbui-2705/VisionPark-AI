import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'
import { LoginPage } from '../../src/modules/auth/LoginPage.tsx'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('LoginPage', () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  function renderLogin(initial = '/login') {
    return render(
      <MemoryRouter initialEntries={[initial]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/station" element={<div>station page</div>} />
            <Route path="/station/scan" element={<div>station page</div>} />
            <Route path="/admin/dashboard" element={<div>dashboard page</div>} />
            <Route path="/admin/lanes" element={<div>lanes page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )
  }

  it('validates required', async () => {
    renderLogin()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /đăng nhập/i }))
    expect(await screen.findByText(/Tên đăng nhập không được để trống/i)).toBeInTheDocument()
  })

  it('shows 401 message', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      jsonResponse({ code: 'UNAUTHENTICATED', message: 'Unauthorized' }, 401),
    )
    renderLogin()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Tên đăng nhập'), 'admin')
    await user.type(screen.getByLabelText('Mật khẩu'), 'wrong')
    await user.click(screen.getByRole('button', { name: /đăng nhập/i }))
    expect(await screen.findByText(/Tên đăng nhập hoặc mật khẩu không đúng/i)).toBeInTheDocument()
  })

  it('redirects on success (ADMIN -> lanes or returnUrl)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const u = String(url)
      if (u.includes('/auth/login')) return jsonResponse({ access_token: 'tok', token_type: 'bearer' })
      if (u.includes('/auth/me')) return jsonResponse({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      return jsonResponse({}, 200)
    })
    renderLogin()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Tên đăng nhập'), 'admin')
    await user.type(screen.getByLabelText('Mật khẩu'), 'pass')
    await user.click(screen.getByRole('button', { name: /đăng nhập/i }))
    await waitFor(() => expect(screen.getByText(/dashboard page/i)).toBeInTheDocument())
  })
})
