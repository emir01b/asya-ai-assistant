import { describe, it, expect, vi } from "vitest";
import { SpeechCapture, pcmWav } from "./speech";

function feed(capture: SpeechCapture, amplitude: number, milliseconds: number) {
  for (let t = 0; t < milliseconds; t += 20)
    capture.accept(new Float32Array(20).fill(amplitude), 1000);
}

describe("conversational voice capture", () => {
  it("buffers an immediate reply during the playback tail guard instead of clipping it", async () => {
    const capture = new SpeechCapture();
    capture.onSpeech = vi.fn();
    let recorded: Blob | null = null;
    capture.onRecording = (blob) => {
      recorded = blob;
    };
    for (let t = 0; t < 180; t += 20)
      capture.accept(new Float32Array(20).fill(0.1), 1000, false);
    expect(capture.onSpeech).not.toHaveBeenCalled();
    feed(capture, 0.1, 80);
    feed(capture, 0, 1200);
    expect(capture.onSpeech).toHaveBeenCalledTimes(1);
    expect(recorded).not.toBeNull();
    const data = new DataView(await (recorded! as Blob).arrayBuffer());
    expect(data.getUint32(40, true) / 2).toBeGreaterThanOrEqual(400);
  });
  it("rejects a keyboard-like transient rather than interrupting the assistant", () => {
    const capture = new SpeechCapture();
    capture.onSpeech = vi.fn();
    capture.onRecording = vi.fn();
    feed(capture, 0.3, 80);
    feed(capture, 0, 1400);
    expect(capture.onSpeech).not.toHaveBeenCalled();
    expect(capture.onRecording).not.toHaveBeenCalled();
  });
  it("keeps speech onset in PCM pre-roll and trims long trailing silence", async () => {
    const capture = new SpeechCapture();
    capture.onSpeech = vi.fn();
    let recording: Blob | null = null;
    capture.onRecording = (blob) => {
      recording = blob;
    };
    feed(capture, 0.007, 160);
    feed(capture, 0.12, 500);
    feed(capture, 0, 1100);
    expect(capture.onSpeech).toHaveBeenCalledTimes(1);
    expect(recording).not.toBeNull();
    const data = new DataView(await (recording! as Blob).arrayBuffer());
    expect(data.getInt16(44, true)).toBeGreaterThan(0);
    expect(data.getUint32(40, true) / 2).toBeLessThan(1000);
  });
  it("ignores all microphone input through the full answer, then resumes for the next turn", () => {
    const capture = new SpeechCapture();
    capture.onSpeech = vi.fn();
    capture.onRecording = vi.fn();
    capture.setSuspended(true);
    feed(capture, 0.15, 500);
    feed(capture, 0, 1200);
    expect(capture.onSpeech).not.toHaveBeenCalled();
    expect(capture.onRecording).not.toHaveBeenCalled();
    capture.setSuspended(false);
    feed(capture, 0.15, 500);
    feed(capture, 0, 1200);
    expect(capture.onRecording).toHaveBeenCalledTimes(1);
  });
  it("discards a partial utterance if the user changes conversation", () => {
    const capture = new SpeechCapture();
    capture.onRecording = vi.fn();
    feed(capture, 0.15, 300);
    capture.reset();
    feed(capture, 0, 1400);
    expect(capture.onRecording).not.toHaveBeenCalled();
  });
  it("writes a bounded mono PCM WAV with the actual capture sample rate", async () => {
    const data = new DataView(
      await pcmWav(new Float32Array([1, -1, 0]), 48000).arrayBuffer(),
    );
    expect(data.getUint32(24, true)).toBe(48000);
    expect(data.getUint16(22, true)).toBe(1);
    expect(data.getInt16(44, true)).toBe(32767);
    expect(data.getInt16(46, true)).toBe(-32768);
  });
});
