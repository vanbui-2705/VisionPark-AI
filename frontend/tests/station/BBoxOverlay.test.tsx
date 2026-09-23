import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import BBoxOverlay from "../../src/modules/station/components/BBoxOverlay";
describe("BBoxOverlay", () => {
  it("keeps source coordinates in a responsive SVG viewBox", () => {
    render(<BBoxOverlay bbox={[120, 340, 250, 410]} sourceWidth={1920} sourceHeight={1080} />);
    const svg = screen.getByTestId("bbox-overlay");
    const rect = screen.getByTestId("bbox-rect");
    expect(svg).toHaveAttribute("viewBox", "0 0 1920 1080");
    expect(rect).toHaveAttribute("x", "120");
    expect(rect).toHaveAttribute("width", "130");
  });
});
