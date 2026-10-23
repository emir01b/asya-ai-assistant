import { audioUrl } from "./api";
import { SpeechCapture } from "./speech";

export class AudioQueue {
  pending: string[] = [];
  current: HTMLAudioElement | null = null;
  generation = 0;
  onState: (speaking: boolean) => void = () => {};
  onError: (message: string) => void = () => {};
  output = "";
  private buffered = new Map<string, HTMLAudioElement>();
  push(id: string) {
    const audio = new Audio(audioUrl(id));
    audio.preload = "auto";
    audio.load?.();
    this.buffered.set(id, audio);
    this.pending.push(id);
    if (!this.current) void this.playNext(this.generation);
  }
  async playNext(generation: number) {
    if (generation !== this.generation) return;
    const id = this.pending.shift();
    if (!id) {
      this.current = null;
      this.onState(false);
      return;
    }
    const audio = this.buffered.get(id) || new Audio(audioUrl(id));
    this.buffered.delete(id);
    this.current = audio;
    this.onState(true);
    const next = () => {
      if (generation === this.generation) {
        this.current = null;
        void this.playNext(generation);
      }
    };
    audio.onended = next;
    audio.onerror = next;
    if (this.output && "setSinkId" in audio)
      await (
        audio as HTMLAudioElement & { setSinkId: (id: string) => Promise<void> }
      )
        .setSinkId(this.output)
        .catch(() =>
          this.onError(
            "Seçilen ses çıkışı kullanılamadı; sistem varsayılanı kullanılıyor.",
          ),
        );
    if (generation !== this.generation) return;
    try {
      await audio.play();
    } catch {
      this.onState(false);
      this.onError(
        "Otomatik ses oynatılamadı. Ses kuyruğunu oynat düğmesine basın.",
      );
    }
  }
  async resume() {
    if (!this.current) return;
    try {
      await this.current.play();
      this.onState(true);
    } catch {
      this.onError("Ses oynatılamadı. Tarayıcı ses izinlerini kontrol edin.");
    }
  }
  stop() {
    this.generation++;
    this.pending = [];
    for (const audio of this.buffered.values()) {
      audio.pause();
      audio.src = "";
    }
    this.buffered.clear();
    if (this.current) {
      this.current.pause();
      this.current.src = "";
      this.current = null;
    }
    this.onState(false);
  }
}

export class Microphone {
  context: AudioContext | null = null;
  stream: MediaStream | null = null;
  active = false;
  threshold = 0.018;
  silenceMs = 1000;
  onLevel: (level: number) => void = () => {};
  onSpeech: () => void = () => {};
  onRecording: (blob: Blob) => void = () => {};
  private capture = new SpeechCapture();
  private node: AudioWorkletNode | null = null;
  private sequence = 0;
  private cooldownUntil = 0;
  setSuspended(value: boolean) {
    if (this.capture.suspended && !value)
      this.cooldownUntil = performance.now() + 180;
    this.capture.setSuspended(value);
  }
  async start(device: string) {
    const sequence = ++this.sequence;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        deviceId: device ? { exact: device } : undefined,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    if (sequence !== this.sequence) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    this.stream = stream;
    const context = new AudioContext();
    this.context = context;
    await context.audioWorklet.addModule("/audio-capture-worklet.js");
    if (sequence !== this.sequence) {
      if (context.state !== "closed") await context.close();
      return;
    }
    const source = context.createMediaStreamSource(stream);
    this.capture.threshold = this.threshold;
    this.capture.silenceMs = this.silenceMs;
    this.capture.onSpeech = () => this.onSpeech();
    this.capture.onRecording = (blob) => this.onRecording(blob);
    const node = new AudioWorkletNode(context, "voice-capture");
    this.node = node;
    const mute = context.createGain();
    mute.gain.value = 0;
    source.connect(node);
    node.connect(mute);
    mute.connect(context.destination);
    node.port.onmessage = (event) => {
      if (!this.active || sequence !== this.sequence) return;
      const frame = event.data as Float32Array;
      this.onLevel(
        Math.sqrt(frame.reduce((sum, x) => sum + x * x, 0) / frame.length),
      );
      this.capture.accept(
        frame,
        context.sampleRate,
        performance.now() >= this.cooldownUntil,
      );
    };
    this.active = true;
    await context.resume();
  }
  stop(deliver = true) {
    this.sequence++;
    this.active = false;
    if (deliver && this.context) this.capture.finish(this.context.sampleRate);
    else this.capture.reset();
    if (this.node) {
      this.node.port.onmessage = null;
      this.node.disconnect();
      this.node = null;
    }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.context && this.context.state !== "closed")
      void this.context.close();
    this.context = null;
    this.onLevel(0);
  }
}
