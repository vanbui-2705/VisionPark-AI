import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient, getApiBaseUrl } from '../../src/api/client.ts'
import { removeToken, setToken } from '../../src/api/token.ts'
import { DetectionImage } from '../../src/components/DetectionImage.tsx'

afterEach(() => {
  removeToken()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('Authenticated detection images', () => {
  it('uses the shared bearer client and releases the object URL on cleanup', async () => {
    setToken('synthetic-test-token')
    const fetch = vi.fn().mockResolvedValue(new Response('private image', {
      headers: { 'Content-Type': 'image/jpeg' },
    }))
    vi.stubGlobal('fetch', fetch)
    URL.createObjectURL = vi.fn().mockReturnValue('blob:private-image')
    URL.revokeObjectURL = vi.fn()
    const src = `${getApiBaseUrl()}/api/v1/alpr/media/private.jpg`
    const view = render(<DetectionImage src={src} />)
    const image = await screen.findByRole('img')
    expect(image).toHaveAttribute('src', 'blob:private-image')
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer synthetic-test-token')
    view.unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:private-image')
  })

  it('keeps local previews and third party images out of the authenticated fetch path', () => {
    const getBlob = vi.spyOn(apiClient, 'getBlob')
    const view = render(<DetectionImage src="blob:local-preview" />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'blob:local-preview')
    view.rerender(<DetectionImage src="https://example.com/public.jpg" />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://example.com/public.jpg')
    expect(getBlob).not.toHaveBeenCalled()
    view.unmount()
  })

  it('discards a response after the image source changes', async () => {
    let complete: ((blob: Blob) => void) | undefined
    vi.spyOn(apiClient, 'getBlob').mockImplementation(() => new Promise(resolve => { complete = resolve }))
    URL.createObjectURL = vi.fn()
    const view = render(<DetectionImage src={`${getApiBaseUrl()}/api/v1/alpr/media/private.jpg`} />)
    view.rerender(<DetectionImage src="blob:next-preview" />)
    complete?.(new Blob(['stale']))
    await waitFor(() => expect(screen.getByRole('img')).toHaveAttribute('src', 'blob:next-preview'))
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    view.unmount()
  })
})
