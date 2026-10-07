import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAlprDetection } from "../../src/modules/station/hooks/useAlprDetection";
import * as api from "../../src/modules/station/api";

const result = (plate: string, x: number) => ({
  detection_id: `${plate}-${x}`,
  raw_plate_number: `${plate.slice(0, 2)}-${plate.slice(2)}`,
  normalized_plate_number: plate,
  bbox: [x, 10, x + 100, 60] as [number, number, number, number],
  confidence: 0.94,
  processing_time_ms: 20,
  model_version: "test",
  requires_confirmation: false,
});

describe("Station consensus", () => {
  it("accepts an image without waiting for multiple video frames", async () => {
    vi.spyOn(api, "createDetection").mockResolvedValue(result("29A12345", 10));
    const hook = renderHook(() => useAlprDetection());
    await act(async () => { await hook.result.current.detect(new Blob(), "lane", { inputKind: "IMAGE_UPLOAD" }); });
    expect(hook.result.current.state).toBe("stable");
  });

  it("ignores an old response after switching the input and prevents parallel inference", async () => {
    let complete!: (value: ReturnType<typeof result>) => void;
    vi.spyOn(api, "createDetection").mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    const hook = renderHook(() => useAlprDetection());
    let pending!: Promise<unknown>;
    act(() => { pending = hook.result.current.detect(new Blob(), "lane"); });
    act(() => hook.result.current.reset());
    await expect(hook.result.current.detect(new Blob(), "new-lane", { inputKind: "IMAGE_UPLOAD" })).rejects.toMatchObject({ code: "REQUEST_IN_PROGRESS" });
    await act(async () => { complete(result("29A12345", 10)); await pending; });
    expect(hook.result.current.state).toBe("idle");
    expect(hook.result.current.result).toBeNull();
  });

  it("keeps a single candidate and stabilizes after a 2/3 consensus", async () => {
    vi.spyOn(api, "createDetection")
      .mockResolvedValueOnce(result("29A12345", 10))
      .mockResolvedValueOnce(result("29A12345", 12));
    const hook = renderHook(() => useAlprDetection());
    const image = new Blob(["frame"], { type: "image/jpeg" });

    await act(async () => { await hook.result.current.detect(image, "lane-in"); });
    expect(hook.result.current.state).toBe("needs_confirmation");
    await act(async () => { await hook.result.current.detect(image, "lane-in"); });
    expect(hook.result.current.state).toBe("stable");
    expect(hook.result.current.result?.detection_id).toBe("29A12345-12");
    expect(hook.result.current.result?.normalized_plate_number).toBe("29A12345");
  });
});
