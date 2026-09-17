import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MockProviderBanner } from '../../src/components/MockProviderBanner.tsx'

function j(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }

describe('MockProviderBanner', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows banner when provider is mock', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      if (String(u).includes('/health/ready')) return j({ status: 'ready', alpr: { ready: true, provider: 'mock', model_version: 'mock-alpr-0.1.0' } })
      return j({})
    })
    render(<MemoryRouter><MockProviderBanner /></MemoryRouter>)
    expect(await screen.findByText(/CHẾ ĐỘ MÔ PHỎNG ALPR/i)).toBeInTheDocument()
  })

  it('does not show mock banner when provider is real', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      if (String(u).includes('/health/ready')) return j({ status: 'ready', alpr: { ready: true, provider: 'yolo' } })
      return j({})
    })
    render(<MemoryRouter><MockProviderBanner /></MemoryRouter>)
    await new Promise((r) => setTimeout(r, 50))
    expect(screen.queryByText(/CHẾ ĐỘ MÔ PHỎNG/i)).not.toBeInTheDocument()
  })

  it('shows unknown status when health fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => { throw new Error('network') })
    render(<MemoryRouter><MockProviderBanner /></MemoryRouter>)
    expect(await screen.findByText(/Không xác định trạng thái ALPR/i)).toBeInTheDocument()
  })
})
