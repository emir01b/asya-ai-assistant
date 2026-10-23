import type { GenerationRequest, Job, Settings } from "./types";
export const API = "/api/v1";
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(API + path, {
    ...init,
    headers: {
      ...(init.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  }
  return response.json();
}
export const audioUrl = (id: string, format = "wav") =>
  `${API}/audio/${encodeURIComponent(id)}?format=${format}`;
export const seconds = (n: number | undefined | null) =>
  n == null ? "Ölçülmedi" : `${n.toFixed(2)} sn`;
export const date = (v: string) => new Date(v).toLocaleString("tr-TR");
export const statusLabel: Record<string, string> = {
  queued: "Sırada",
  running: "Üretiliyor",
  cancelling: "Segmentin bitmesi bekleniyor",
  cancelled: "İptal edildi",
  completed: "Hazır",
  failed: "Hata",
  idle: "Hazır",
  listening: "Dinleniyor",
  speech_detected: "Konuşma algılandı",
  transcribing: "Yazıya dönüştürülüyor",
  thinking: "Düşünüyor",
  synthesizing: "Ses hazırlanıyor",
  speaking: "Konuşuyor",
  interrupted: "Kesildi",
  error: "Hata",
};

export const generateAudio = (request: GenerationRequest) =>
  api<Job>("/tts/generate", { method: "POST", body: JSON.stringify(request) });
export const saveSettings = (settings: Settings) =>
  api<Settings>("/settings", { method: "PUT", body: JSON.stringify(settings) });
