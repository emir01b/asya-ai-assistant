import { useState, useEffect, useRef, type ReactNode } from "react";
import { AudioLines, ArrowDownToLine } from "lucide-react";
import { api, audioUrl } from "../api";
import { languageNames } from "../catalog";
import type { Voice } from "../types";
export type Feedback = {
  fail: (e: unknown) => void;
  notify: (s: string) => void;
};

export function IconButton({
  children,
  label,
  onClick,
  disabled = false,
}: {
  children: ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="icon-button"
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function Empty({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty">
      <AudioLines size={30} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

export function Tag({
  children,
  good = false,
}: {
  children: ReactNode;
  good?: boolean;
}) {
  return (
    <span className={`tag ${good ? "good" : ""}`}>
      <i />
      {children}
    </span>
  );
}

export function LanguageSelect({
  value,
  onChange,
  auto = false,
}: {
  value: string;
  onChange: (s: string) => void;
  auto?: boolean;
}) {
  return (
    <select
      aria-label="Dil"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {auto && <option value="auto">Otomatik algıla</option>}
      {Object.entries(languageNames).map(([id, name]) => (
        <option key={id} value={id}>
          {name}
        </option>
      ))}
    </select>
  );
}

export function VoiceSelect({
  voices,
  value,
  onChange,
}: {
  voices: Voice[];
  value: string;
  onChange: (s: string) => void;
}) {
  return (
    <select
      aria-label="Ses profili"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">Modelin varsayılan sesi</option>
      {voices.map((v) => (
        <option key={v.id} value={v.id}>
          {v.name}
        </option>
      ))}
    </select>
  );
}

export function Player({
  asset,
  label = "Üretilen ses",
  output = "",
}: {
  asset: string;
  label?: string;
  output?: string;
}) {
  const [peaks, setPeaks] = useState<number[]>([]);
  const ref = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    let active = true;
    api<{ peaks: number[] }>(`/audio/${asset}/peaks`)
      .then((v) => {
        if (active) setPeaks(v.peaks);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [asset]);
  useEffect(() => {
    const audio = ref.current as
      (HTMLAudioElement & { setSinkId?: (s: string) => Promise<void> }) | null;
    if (output && audio?.setSinkId)
      void audio.setSinkId(output).catch(() => {});
  }, [output]);
  return (
    <div className="player">
      <div className="player-top">
        <span>
          <AudioLines size={17} />
          {label}
        </span>
        <div className="inline">
          <a className="text-link" href={audioUrl(asset)} download>
            <ArrowDownToLine size={14} />
            WAV
          </a>
          <a className="text-link" href={audioUrl(asset, "mp3")} download>
            MP3
          </a>
        </div>
      </div>
      <div className="waveform" aria-label="Gerçek ses dalga formu">
        {peaks.map((p, i) => (
          <i key={i} style={{ height: `${Math.max(3, p * 100)}%` }} />
        ))}
      </div>
      <audio ref={ref} controls preload="metadata" src={audioUrl(asset)} />
    </div>
  );
}

export function Range({
  label,
  value,
  onChange,
  max = 1,
  min = 0,
  step = 0.05,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  max?: number;
  min?: number;
  step?: number;
}) {
  return (
    <div className="range">
      <div>
        <label htmlFor={label}>{label}</label>
        <output>{value.toFixed(2)}</output>
      </div>
      <input
        id={label}
        aria-label={label}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="range-ends">
        <span>Düşük</span>
        <span>Yüksek</span>
      </div>
    </div>
  );
}

export function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="panel stat">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export function StatusRow({
  label,
  value,
  good,
}: {
  label: string;
  value: string;
  good: boolean;
}) {
  return (
    <div className="status-row">
      <span>{label}</span>
      <Tag good={good}>{value}</Tag>
    </div>
  );
}
