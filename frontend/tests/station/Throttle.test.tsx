import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAlprDetection } from "../../src/modules/station/hooks/useAlprDetection";
import * as api from "../../src/modules/station/api";
describe("ALPR throttle", () => {
  it("rejects a second request while first is processing", async () => {
    let release!: () => void;
    vi.spyOn(api, "createDetection").mockImplementation(() => new Promise(resolve => {
      release = () => resolve({
        detection_id: "1",
        raw_plate_number: null,
        normalized_plate_number: "29A12345",
        bbox: null,
        confidence: .9,
        processing_time_ms: 1,
        model_version: "test",
        requires_confirmation: false
      });
    }));
    const {
      result
    } = renderHook(() => useAlprDetection());
    const image = new Blob(["x"], {
      type: "image/jpeg"
    });
    let first!: Promise<unknown>;
    act(() => {
      first = result.current.detect(image, "lane-1");
    });
    await expect(result.current.detect(image, "lane-1")).rejects.toMatchObject({
      code: "REQUEST_IN_PROGRESS"
    });
    release();
    await first;
  });
});
