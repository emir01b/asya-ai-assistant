import type { components } from "./generated-api";
export type Voice = components["schemas"]["Voice"];
export type Segment = components["schemas"]["Segment"];
export type Metrics = components["schemas"]["Metrics"] & {
  llm_first_token_seconds?: number | null;
};
export type Job = components["schemas"]["Job"];
export type Settings = Required<components["schemas"]["Settings"]>;
type GenerationSchema = components["schemas"]["Generation"];
export type GenerationRequest = Pick<GenerationSchema, "text"> &
  Partial<Omit<GenerationSchema, "text">>;
export interface LMStatus {
  connected: boolean;
  models: { id: string }[];
  error: string | null;
}
export interface EngineStatus {
  loaded: boolean;
  device: string | null;
  active: string | null;
  pending: number;
  model_load_seconds: number | null;
  last_seconds: number | null;
}
export interface SystemStatus {
  network?: {
    lan_enabled: boolean;
    lan_url: string | null;
    https_url?: string | null;
  };
  tts: EngineStatus;
  stt: {
    installed: boolean;
    loaded: boolean;
    device: string | null;
    error: string | null;
  };
  lm: LMStatus;
  offline: boolean;
  counts: { voices: number; generations: number; conversations: number };
}
export interface GPU {
  available: boolean;
  name?: string;
  total_mb?: number;
  used_mb?: number;
  free_mb?: number;
  utilization?: number;
  error?: string;
}
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  interrupted?: boolean;
  job_ids?: string[];
  metrics?: Metrics;
}
export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  message_count?: number;
  messages?: Message[];
}
export interface Diagnostics {
  benchmarks: ({
    id: string;
    source: string;
    created_at: string;
    seconds?: number;
    device?: string;
  } & Metrics)[];
  errors: { id: string; source: string; message: string; created_at: string }[];
  tts: EngineStatus;
}
export interface Transcript {
  text: string;
  language: string;
  seconds: number;
  device: string;
  warning?: string;
  segments: { start: number; end: number; text: string }[];
}
