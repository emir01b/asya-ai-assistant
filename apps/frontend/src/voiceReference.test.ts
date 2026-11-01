import { describe, expect, it } from "vitest";
import {
  MAX_REFERENCE_BYTES,
  referenceClipError,
  referenceFileError,
} from "./voiceReference";

describe("voice upload validation", () => {
  it("accepts the exact limits and rejects larger or longer recordings", () => {
    expect(referenceFileError(MAX_REFERENCE_BYTES, 300)).toBeNull();
    expect(referenceFileError(MAX_REFERENCE_BYTES + 1, 10)).toContain("200 MB");
    expect(referenceFileError(1024, 300.01)).toContain("5 dakika");
    expect(referenceFileError(1024, 0.25)).toBeNull();
    for (const invalid of [0, 0.24, Infinity, NaN])
      expect(referenceFileError(1024, invalid)).not.toBeNull();
  });
  it("keeps clip selection in the recording and accepts zero as the beginning", () => {
    expect(referenceClipError(0, 8, 15)).toBeNull();
    expect(referenceClipError(2, 8, 15)).toBeNull();
    expect(referenceClipError(0, 0.25, 15)).toBeNull();
    expect(referenceClipError(0, 12, 15)).toBeNull(); // 6–10s is advice, not a hard limit.
    for (const [start, end] of [
      [-1, 8],
      [8, 2],
      [2, 16],
      [2, 2.1],
      [NaN, 8],
    ])
      expect(referenceClipError(start, end, 15)).not.toBeNull();
  });
});
