import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { UserDetailPage } from '../../src/modules/users/UserDetailPage.tsx'


function json(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}


afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})


describe('UserDetailPage building assignment', () => {
  it('shows the building assigned to the account', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (request) => {
      const url = String(request)
      if (url.includes('/api/v1/buildings')) {
        return json([{ id: 'building-1', name: 'Assigned building' }])
      }
      if (url.includes('/api/v1/users/user-1')) {
        return json({
          id: 'user-1',
          username: 'operator-1',
          display_name: 'Operator One',
          email: null,
          role: 'OPERATOR',
          building_id: 'building-1',
          is_active: true,
          last_login_at: null,
          created_at: '2026-11-13T00:00:00Z',
        })
      }
      return json({})
    })

    render(
      <MemoryRouter initialEntries={['/admin/users/user-1']}>
        <Routes>
          <Route path="/admin/users/:id" element={<UserDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByDisplayValue('Assigned building')).toBeInTheDocument()
  })
})
