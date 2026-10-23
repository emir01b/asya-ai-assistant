/** Frame-based VAD with onset confirmation and PCM pre-roll. No wall-clock timers. */
export class SpeechCapture {
  threshold = 0.018;
  silenceMs = 1000;
  attackMs = 140;
  minVoiceMs = 200;
  suspended = false;
  speaking = false;
  onSpeech: () => void = () => {};
  onRecording: (blob: Blob) => void = () => {};
  private preRoll: Float32Array[] = [];
  private chunks: Float32Array[] = [];
  private preSamples = 0;
  private samples = 0;
  private candidateMs = 0;
  private voicedMs = 0;
  private quietMs = 0;

  reset() {
    this.preRoll = [];
    this.chunks = [];
    this.preSamples = 0;
    this.samples = 0;
    this.candidateMs = 0;
    this.voicedMs = 0;
    this.quietMs = 0;
    this.speaking = false;
  }
  setSuspended(value: boolean) {
    if (this.suspended === value) return;
    this.suspended = value;
    this.reset();
  }
  accept(frame: Float32Array, sampleRate: number, allowStart = true) {
    if (this.suspended) return;
    const ms = (frame.length / sampleRate) * 1000;
    const rms = Math.sqrt(
      frame.reduce((sum, x) => sum + x * x, 0) / frame.length,
    );
    if (!this.speaking) {
      this.preRoll.push(frame);
      this.preSamples += frame.length;
      while (this.preSamples > sampleRate * 0.32 && this.preRoll.length > 1)
        this.preSamples -= this.preRoll.shift()!.length;
      this.candidateMs = rms >= this.threshold ? this.candidateMs + ms : 0;
      if (!allowStart || this.candidateMs < this.attackMs) return;
      this.speaking = true;
      this.voicedMs = this.candidateMs;
      this.chunks = this.preRoll;
      this.samples = this.preSamples;
      this.preRoll = [];
      this.preSamples = 0;
      this.quietMs = 0;
      this.onSpeech();
      return;
    }
    this.chunks.push(frame);
    this.samples += frame.length;
    if (rms >= this.threshold * 0.65) {
      this.voicedMs += ms;
      this.quietMs = 0;
    } else this.quietMs += ms;
    if (this.quietMs >= this.silenceMs || this.samples >= sampleRate * 60)
      this.finish(sampleRate);
  }
  finish(sampleRate: number) {
    const chunks = this.chunks,
      samples = this.samples,
      voiced = this.voicedMs;
    const trailing = Math.max(0, this.quietMs - 180);
    this.reset();
    if (voiced < this.minVoiceMs || !samples) return;
    const pcm = new Float32Array(samples);
    let offset = 0;
    for (const chunk of chunks) {
      pcm.set(chunk, offset);
      offset += chunk.length;
    }
    this.onRecording(
      pcmWav(
        pcm.subarray(
          0,
          Math.max(1, samples - Math.floor((trailing * sampleRate) / 1000)),
        ),
        sampleRate,
      ),
    );
  }
}

export function pcmWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++)
      view.setUint8(offset + i, value.charCodeAt(i));
  };
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++)
    view.setInt16(
      44 + i * 2,
      Math.round(
        Math.max(-1, Math.min(1, samples[i])) *
          (samples[i] < 0 ? 32768 : 32767),
      ),
      true,
    );
  return new Blob([buffer], { type: "audio/wav" });
}
