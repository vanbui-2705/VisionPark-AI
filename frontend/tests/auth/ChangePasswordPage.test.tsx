import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'
import { ChangePasswordPage } from '../../src/modules/auth/ChangePasswordPage.tsx'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('visionpark.access_token', 'temporary-token')
    vi.restoreAllMocks()
  })

  it('clears the local session without calling logout with the revoked token', async () => {
    const requests: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const path = String(url)
      requests.push(path)
      if (path.includes('/auth/me')) {
        return jsonResponse({
          id: '1',
          username: 'building-admin',
          display_name: 'Building Admin',
          role: 'BUILDING_ADMIN',
          is_active: true,
          must_change_password: true,
        })
      }
      if (path.includes('/auth/change-password')) {
        return jsonResponse({ status: 'changed', sign_in_required: true })
      }
      if (path.includes('/auth/logout')) {
        return jsonResponse({ code: 'UNAUTHENTICATED', message: 'Token revoked' }, 401)
      }
      return jsonResponse({})
    })

    render(
      <MemoryRouter initialEntries={['/change-password']}>
        <AuthProvider>
          <Routes>
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="/login" element={<div>login page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Mật khẩu hiện tại'), 'temporary-password')
    await user.type(screen.getByLabelText('Mật khẩu mới'), 'new-private-password')
    await user.click(screen.getByRole('button', { name: /Đổi mật khẩu/i }))

    await waitFor(() => expect(screen.getByText('login page')).toBeInTheDocument())
    expect(requests.some((path) => path.includes('/auth/logout'))).toBe(false)
    expect(localStorage.getItem('visionpark.access_token')).toBeNull()
  })
})
