import React from "react";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VideoPlayer from "../../src/modules/station/components/VideoPlayer";
import VideoSelector from "../../src/modules/station/components/VideoSelector";
beforeEach(() => {
  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: vi.fn().mockResolvedValue(undefined)
  });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", {
    configurable: true,
    value: vi.fn()
  });
});
describe("VideoPlayer", () => {
  it("has play pause replay controls", () => {
    render(<VideoPlayer videoUrl="blob:test" />);
    expect(screen.getByRole("button", {
      name: "Play"
    })).toBeInTheDocument();
    expect(screen.getByRole("button", {
      name: "Pause"
    })).toBeInTheDocument();
    expect(screen.getByRole("button", {
      name: "Replay"
    })).toBeInTheDocument();
  });
  it("plays and pauses", async () => {
    render(<VideoPlayer videoUrl="blob:test" />);
    await userEvent.click(screen.getByRole("button", {
      name: "Play"
    }));
    await userEvent.click(screen.getByRole("button", {
      name: "Pause"
    }));
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
  });
  it("accepts an MP4 by extension and passes its local preview URL", async () => {
    const selected = vi.fn()
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:selected-video')
    render(<VideoSelector onVideoSelected={selected} />)
    const file = new File(['mp4'], 'vehicle.MP4', { type: '' })
    await userEvent.upload(screen.getByLabelText('Video MP4'), file)
    expect(selected).toHaveBeenCalledWith(file, 'blob:selected-video')
  });
  it("samples a lightweight frame for fire monitoring while video is playing", async () => {
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
    expect(monitor.mock.calls[0][0]).toMatchObject({ type: 'image/jpeg' })
    vi.useRealTimers()
  });
});
