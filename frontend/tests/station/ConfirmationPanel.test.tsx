import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ConfirmationPanel from "../../src/modules/station/components/ConfirmationPanel";
const result = {
  detection_id: "d1",
  raw_plate_number: "29A-123.45",
  normalized_plate_number: "29A12345",
  bbox: null,
  confidence: .91,
  processing_time_ms: 25,
  model_version: "mock",
  requires_confirmation: false
};
describe("ConfirmationPanel", () => {
  it("confirms accepted result", async () => {
    const ok = vi.fn().mockResolvedValue(undefined);
    render(<ConfirmationPanel result={result} onConfirmCorrect={ok} onConfirmCorrection={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", {
      name: /biển số đúng/i
    }));
    expect(ok).toHaveBeenCalledWith("d1");
  });
  it("normalizes correction", async () => {
    const fix = vi.fn().mockResolvedValue(undefined);
    render(<ConfirmationPanel result={result} onConfirmCorrect={vi.fn()} onConfirmCorrection={fix} />);
    await userEvent.click(screen.getByRole("button", {
      name: /sai/i
    }));
    const input = screen.getByLabelText(/biển số chính xác/i);
    await userEvent.clear(input);
    await userEvent.type(input, "30f-123.45");
    await userEvent.click(screen.getByRole("button", {
      name: /xác nhận sửa/i
    }));
    expect(fix).toHaveBeenCalledWith("d1", "30F12345");
  });
});
