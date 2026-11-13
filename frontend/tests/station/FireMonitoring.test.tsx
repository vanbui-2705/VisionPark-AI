import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import StationPage from '../../src/modules/station/StationPage'
import VideoPlayer from '../../src/modules/station/components/VideoPlayer'
import { AuthContext, type AuthContextValue } from '../../src/modules/auth/AuthContext'

const response = (body: unknown) => new Response(JSON.stringify(body))
const auth = {
  user: { id: 'operator', username: 'operator', display_name: 'Operator', active: true, building_id: 'building', role: 'OPERATOR' },
  initialized: true,
  isAuthenticated: true,
  loading: false,
} as AuthContextValue

beforeEach(() => { localStorage.clear() })
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks() })

describe('Station fire monitoring', () => {
  it('checks the same uploaded image and shows a dismissible fire alert', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const path = String(url)
      if (path.includes('/lanes/active')) return response([
        { id: 'in', name: 'Entry', direction: 'IN', is_active: true, building_id: 'building', camera_id: 'entry-camera' },
      ])
      if (path.includes('/customer-classes')) return response([{ id: 'class', name: 'Visitor' }])
      if (path.endsWith('/alpr/fire-detection')) return response([{
        building_id: 'building', camera_id: 'entry-camera', zone_code: null,
        event_type: 'FIRE', confidence: 0.92, confirmed_frame_count: 1,
        bbox: [5, 6, 70, 80], timestamp: '2026-11-13T10:00:00Z', status: 'VERIFYING',
      }])
      if (path.endsWith('/alpr/detections')) return response({
        detection_id: null, raw_plate_number: '59X12345', normalized_plate_number: '59X12345',
        bbox: [1, 2, 30, 40], confidence: 0.94, processing_time_ms: 25,
        model_version: 'test', requires_confirmation: false,
      })
      return response([])
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:selected-vehicle')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)

    render(<AuthContext.Provider value={auth}><StationPage /></AuthContext.Provider>)
    await screen.findByRole('option', { name: 'Entry - IN' })
    fireEvent.change(screen.getByLabelText('Lane'), { target: { value: 'in' } })
    fireEvent.change(screen.getByLabelText('Chế độ nhận diện'), { target: { value: 'image' } })
    fireEvent.change(screen.getByLabelText('Ảnh đầu vào'), {
      target: { files: [new File(['jpeg'], 'vehicle.jpg', { type: 'image/jpeg' })] },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Nhận diện ảnh' }))

    const dialog = await screen.findByRole('alertdialog', { name: 'CẢNH BÁO CHÁY' })
    expect(dialog).toHaveTextContent('Phát hiện lửa tại Entry')
    expect(dialog).toHaveTextContent('92%')
    const fireRequest = fetch.mock.calls.find(([url]) => String(url).endsWith('/alpr/fire-detection'))!
    const form = fireRequest[1]?.body as FormData
    expect(form.get('camera_id')).toBe('entry-camera')
    expect(form.get('building_id')).toBe('building')
    expect(form.get('demo_mode')).toBe('true')
    expect(screen.getByRole('button', { name: 'ĐÃ NHẬN CẢNH BÁO – TẮT' })).toHaveFocus()

    fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'ĐÃ NHẬN CẢNH BÁO – TẮT' }))
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
  })

  it('samples a lightweight fire-monitor frame while video is playing', async () => {
    vi.useFakeTimers()
    const monitor = vi.fn().mockResolvedValue(undefined)
    const drawImage = vi.fn()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ drawImage } as unknown as CanvasRenderingContext2D)
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation(callback => callback(new Blob(['fire-frame'], { type: 'image/jpeg' })))
    const { container } = render(<VideoPlayer videoUrl="blob:test" onMonitoringFrame={monitor} />)
    const video = container.querySelector('video')!
    Object.defineProperties(video, {
      readyState: { configurable: true, value: 2 },
      paused: { configurable: true, value: false },
      ended: { configurable: true, value: false },
      videoWidth: { configurable: true, value: 1280 },
      videoHeight: { configurable: true, value: 720 },
    })

    await act(async () => { await vi.advanceTimersByTimeAsync(2500) })
    expect(drawImage).toHaveBeenCalledWith(video, 0, 0, 640, 360)
    expect(monitor).toHaveBeenCalledOnce()
  })
})
