import { useRef, useState } from "react";
import { api, audioUrl } from "../api";
import type { Voice } from "../types";
import { referenceClipError } from "../voiceReference";
import type { Feedback } from "./ui";

export default function ReferenceEditor({
  voice,
  refresh,
  fail,
  notify,
  close,
}: {
  voice: Voice;
  refresh: () => Promise<void>;
  close: () => void;
} & Feedback) {
  const [start, setStart] = useState(voice.reference_start ?? 0);
  const [end, setEnd] = useState(
    voice.reference_end ?? Math.min(8, voice.duration),
  );
  const [busy, setBusy] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  const error = referenceClipError(start, end, voice.duration);
  async function save() {
    if (error) return;
    setBusy(true);
    try {
      await api(`/voices/${voice.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: voice.name,
          language: voice.language,
          exaggeration: voice.exaggeration,
          cfg_weight: voice.cfg_weight,
          reference_start: start,
          reference_end: end,
        }),
      });
      await refresh();
      notify(
        "Referans klibi kaydedildi. Yeni üretimlerde kullanılacak; orijinal kayıt korundu.",
      );
      close();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div
      className="reference-editor"
      aria-label={`${voice.name} referans klibi`}
    >
      <h4>Referans klibini düzenle</h4>
      <p className="help-text">
        Tek konuşmacı, sessiz ortam ve temiz konuşma içeren 6–10 saniye seçin.
        Seçimi dinleyip kaydedin; mevcut profil siz kaydetmeden değişmez. Tam
        kayıt ve orijinal dosya korunur.
      </p>
      <div className="two-cols">
        <label>
          Başlangıç (sn)
          <input
            aria-label="Klip başlangıcı"
            type="number"
            min={0}
            max={voice.duration}
            step={0.1}
            value={start}
            onChange={(e) => {
              audio.current?.pause();
              setStart(Number(e.target.value));
            }}
          />
        </label>
        <label>
          Bitiş (sn)
          <input
            aria-label="Klip bitişi"
            type="number"
            min={0.25}
            max={voice.duration}
            step={0.1}
            value={end}
            onChange={(e) => {
              audio.current?.pause();
              setEnd(Number(e.target.value));
            }}
          />
        </label>
      </div>
      <p className="help-text">Seçili uzunluk: {(end - start).toFixed(2)} sn</p>
      {error && (
        <p className="error-text" role="status">
          {error}
        </p>
      )}
      {!error && (end - start < 6 || end - start > 10) && (
        <p className="help-text">
          Önerilen referans uzunluğu 6–10 saniyedir; temiz ve kesintisiz konuşma
          seçin.
        </p>
      )}
      <audio
        ref={audio}
        controls
        aria-label="Klip önizlemesi"
        src={audioUrl(voice.asset_id)}
        onPlay={(e) => {
          if (error) {
            e.currentTarget.pause();
            return;
          }
          if (
            e.currentTarget.currentTime < start ||
            e.currentTarget.currentTime >= end
          )
            e.currentTarget.currentTime = start;
        }}
        onTimeUpdate={(e) => {
          if (e.currentTarget.currentTime >= end) e.currentTarget.pause();
        }}
      />
      <div className="voice-actions">
        <button
          className="text-link"
          disabled={!!error}
          onClick={() => {
            const current = audio.current;
            if (current) {
              current.currentTime = start;
              void current.play().catch(fail);
            }
          }}
        >
          Seçili klibi dinle
        </button>
        <button
          className="button secondary"
          disabled={busy || !!error}
          onClick={() => void save()}
        >
          {busy ? "Kaydediliyor…" : "Referans klibini kaydet"}
        </button>
        <button className="text-link" disabled={busy} onClick={close}>
          Vazgeç
        </button>
      </div>
    </div>
  );
}
