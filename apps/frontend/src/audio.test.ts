import { describe, it, expect, vi, beforeEach } from "vitest";
import { AudioQueue } from "./audio";
import { api, seconds } from "./api";

class FakeAudio {
  static instances: FakeAudio[] = [];
  onended: (() => void) | null = null;
  onerror: (() => void) | null = null;
  src = "";
  paused = false;
  play = vi.fn(async () => {});
  pause = vi.fn(() => {
    this.paused = true;
  });
  constructor(src: string) {
    this.src = src;
    FakeAudio.instances.push(this);
  }
}
describe("request isolation and playback", () => {
  beforeEach(() => {
    FakeAudio.instances = [];
    vi.stubGlobal("Audio", FakeAudio);
  });
  it("plays segments in order and discards old callbacks after interruption", async () => {
    const queue = new AudioQueue();
    queue.push("old-1");
    queue.push("old-2");
    const first = FakeAudio.instances[0];
    queue.stop();
    queue.push("new-1");
    first.onended?.();
    await Promise.resolve();
    expect(FakeAudio.instances).toHaveLength(3);
    expect(first.paused).toBe(true);
    expect(FakeAudio.instances[2].src).toContain("new-1");
    expect(queue.pending).toHaveLength(0);
  });
  it("plays the next segment only after the current one ends", () => {
    const queue = new AudioQueue();
    queue.push("one");
    queue.push("two");
    expect(FakeAudio.instances).toHaveLength(2);
    expect(queue.current).toBe(FakeAudio.instances[0]);
    FakeAudio.instances[0].onended?.();
    expect(FakeAudio.instances).toHaveLength(2);
    expect(FakeAudio.instances[1].src).toContain("two");
    expect(queue.current).toBe(FakeAudio.instances[1]);
  });
  it("shows server validation errors to callers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        json: async () => ({ detail: "Ses geçersiz" }),
      })),
    );
    await expect(api("/voices")).rejects.toThrow("Ses geçersiz");
  });
  it("does not invent missing timing data", () => {
    expect(seconds(null)).toBe("Ölçülmedi");
    expect(seconds(1.23)).toBe("1.23 sn");
  });
});
