import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VideoPlayer from "../../src/modules/station/components/VideoPlayer";
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
});
