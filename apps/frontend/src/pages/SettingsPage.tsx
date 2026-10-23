import { useState, useEffect } from "react";
import {
  AudioLines,
  Check,
  Cpu,
  Mic,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api";
import {
  Range,
  StatusRow,
  LanguageSelect,
  VoiceSelect,
  type Feedback,
} from "../components/ui";
import type { Settings, LMStatus, Voice, SystemStatus } from "../types";
import LanHttpsSetup from "../components/LanHttpsSetup";

export default function SettingsPage({
  initial,
  lm,
  network,
  refresh,
  fail,
  notify,
  voices,
}: {
  initial: Settings;
  lm: LMStatus | undefined;
  network: SystemStatus["network"];
  refresh: () => Promise<void>;
  voices: Voice[];
} & Feedback) {
  const [value, setValue] = useState(initial);
  const [models, setModels] = useState(lm);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setModels(lm);
  }, [lm]);
  const set = <K extends keyof Settings>(k: K, v: Settings[K]) =>
    setValue((s) => ({ ...s, [k]: v }));
  async function save() {
    setBusy(true);
    try {
      await api("/settings", { method: "PUT", body: JSON.stringify(value) });
      await refresh();
      notify("Ayarlar kaydedildi.");
      return true;
    } catch (e) {
      fail(e);
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function discoverDevices() {
    try {
      if (!window.isSecureContext) {
        throw new Error(
          "Mikrofon için HTTPS gerekir. Sunucu bilgisayarında http://localhost:8000 kullanabilirsiniz.",
        );
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setDevices(await navigator.mediaDevices.enumerateDevices());
    } catch (e) {
      fail(e);
    }
  }
  return (
    <>
      <LanHttpsSetup network={network} />
      <div className="settings-grid">
        <section className="panel padded">
          <h2>
            <Cpu size={18} />
            LM Studio
          </h2>
          <label htmlFor="lm-url">YEREL API ADRESİ</label>
          <input
            id="lm-url"
            value={value.lm_url}
            onChange={(e) => set("lm_url", e.target.value)}
          />
          <p className="help-text">
            LM Studio → Developer → Start Server. Adres /v1 ile bitmelidir.
          </p>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() =>
              void (async () => {
                if (await save()) setModels(await api<LMStatus>("/llm/models"));
              })().catch(fail)
            }
          >
            <RefreshCw size={15} />
            Kaydet ve modelleri tara
          </button>
          {models?.error && <p className="error-text">{models.error}</p>}
          <label htmlFor="llm-model">AKTİF MODEL</label>
          <select
            id="llm-model"
            value={value.llm_model}
            onChange={(e) => set("llm_model", e.target.value)}
          >
            <option value="">Model seçin</option>
            {value.llm_model &&
              !models?.models.some((m) => m.id === value.llm_model) && (
                <option value={value.llm_model}>
                  {value.llm_model} (bağlı değil)
                </option>
              )}
            {models?.models.map((m) => (
              <option key={m.id}>{m.id}</option>
            ))}
          </select>
          <Range
            label="Temperature"
            value={value.temperature}
            max={2}
            onChange={(v) => set("temperature", v)}
          />
          <label htmlFor="system-prompt">SİSTEM PROMPT’U</label>
          <textarea
            id="system-prompt"
            value={value.system_prompt}
            onChange={(e) => set("system_prompt", e.target.value)}
            rows={5}
          />
          <p className="help-text">
            Sesli yanıtlara otomatik olarak doğal cümle ve noktalama kuralları
            eklenir. Ses parçasının sonundaki virgül kısa, cümle sonu daha uzun
            bir duraklama sağlar. Gerçek konuşma temposunu aşağıdaki hız ayarı
            belirler.
          </p>
        </section>
        <section className="panel padded">
          <h2>
            <AudioLines size={18} />
            Ses ve modeller
          </h2>
          <Range
            label="Sohbet konuşma hızı"
            value={value.chat_speech_rate}
            min={0.75}
            max={1.15}
            step={0.05}
            onChange={(v) => set("chat_speech_rate", v)}
          />
          <p className="help-text">
            0,90× sakin tempo, 1,00× modelin doğal hızı. Sesin tonu korunur.
            Yeni sohbet yanıtlarında uygulanır.
          </p>
          <label>TTS CİHAZI</label>
          <select
            aria-label="TTS cihazı"
            value={value.tts_device}
            onChange={(e) =>
              set("tts_device", e.target.value as "cuda" | "cpu")
            }
          >
            <option value="cuda">CUDA · GPU</option>
            <option value="cpu">CPU · Daha yavaş</option>
          </select>
          <label htmlFor="stt-model">WHISPER MODELİ</label>
          <input
            id="stt-model"
            value={value.stt_model}
            onChange={(e) => set("stt_model", e.target.value)}
          />
          <label>STT CİHAZI</label>
          <select
            aria-label="STT cihazı"
            value={value.stt_device}
            onChange={(e) =>
              set("stt_device", e.target.value as "cuda" | "cpu")
            }
          >
            <option value="cuda">CUDA · FP16</option>
            <option value="cpu">CPU · INT8</option>
          </select>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={value.stt_cpu_fallback}
              onChange={(e) => set("stt_cpu_fallback", e.target.checked)}
            />
            GPU hatasında CPU kullan ve uyarı göster
          </label>
          <label>VARSAYILAN DİL</label>
          <LanguageSelect
            value={value.language}
            onChange={(v) => set("language", v)}
          />
          <label>VARSAYILAN SES PROFİLİ</label>
          <VoiceSelect
            voices={voices}
            value={value.default_voice}
            onChange={(v) => set("default_voice", v)}
          />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={value.offline}
              onChange={(e) => set("offline", e.target.checked)}
            />
            Offline model yükleme (yalnızca önbellek)
          </label>
          <p className="help-text">
            İlk Whisper indirmesi için offline seçeneğini kapatın. Önceden
            yüklenen TTS modeli yeniden indirilmez.
          </p>
          <button
            className="button secondary"
            onClick={() =>
              void api("/tts/unload", { method: "POST" })
                .then(() => notify("TTS modeli GPU belleğinden boşaltıldı."))
                .catch(fail)
            }
          >
            TTS modelini boşalt
          </button>
          <button
            className="button secondary"
            onClick={() =>
              void api("/stt/unload", { method: "POST" })
                .then(() => notify("STT modeli bellekten boşaltıldı."))
                .catch(fail)
            }
          >
            STT modelini boşalt
          </button>
        </section>
        <section className="panel padded">
          <h2>
            <Mic size={18} />
            Mikrofon ve VAD
          </h2>
          <button
            className="button secondary"
            onClick={() => void discoverDevices()}
          >
            Ses cihazlarını tara
          </button>
          <label>MİKROFON</label>
          <select
            aria-label="Mikrofon"
            value={value.microphone_id}
            onChange={(e) => set("microphone_id", e.target.value)}
          >
            <option value="">Sistem varsayılanı</option>
            {devices
              .filter((d) => d.kind === "audioinput")
              .map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || d.deviceId}
                </option>
              ))}
          </select>
          <label>SES ÇIKIŞI</label>
          <select
            aria-label="Ses çıkışı"
            value={value.output_id}
            onChange={(e) => set("output_id", e.target.value)}
          >
            <option value="">Sistem varsayılanı</option>
            {devices
              .filter((d) => d.kind === "audiooutput")
              .map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || d.deviceId}
                </option>
              ))}
          </select>
          <Range
            label="VAD enerji eşiği"
            value={value.vad_threshold}
            min={0.001}
            max={0.15}
            step={0.001}
            onChange={(v) => set("vad_threshold", v)}
          />
          <label htmlFor="silence">KONUŞMA SONU SESSİZLİĞİ (MS)</label>
          <input
            id="silence"
            type="number"
            min={300}
            max={3000}
            value={value.vad_silence_ms}
            onChange={(e) => set("vad_silence_ms", Number(e.target.value))}
          />
          <p className="help-text">
            Tarayıcı enerji VAD + Whisper Silero filtresi kullanılır. Mikrofonun
            hoparlör sesini algılamaması için kulaklık önerilir.
          </p>
        </section>
        <section className="panel padded">
          <h2>
            <ShieldCheck size={18} />
            Gizlilik ve çalışma şekli
          </h2>
          <p>
            Tüm ses kayıtları ve konuşmalar sunucu bilgisayarındaki SQLite
            veritabanında ve data klasöründe tutulur.
          </p>
          <StatusRow label="Telemetri" good value="Kapalı" />
          <StatusRow
            label="API erişimi"
            good
            value={
              network?.lan_enabled
                ? "Localhost ve yerel ağ"
                : "Yalnızca localhost"
            }
          />
          {network?.lan_url && (
            <p className="help-text">Yerel ağ adresi: {network.lan_url}</p>
          )}
          {network?.https_url && (
            <p className="help-text">
              HTTPS adresi: <a href={network.https_url}>{network.https_url}</a>
            </p>
          )}
          <StatusRow label="TTS streaming" good value="Cümle segmentleri" />
          <p className="help-text">
            Fish Audio S2 Pro henüz doğrulanmadı. Chatterbox bu eklentiden
            bağımsız çalışır. Masaüstü dağıtımı için React arayüzü ve Python
            backend ayrıdır.
          </p>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={value.debug}
              onChange={(e) => set("debug", e.target.checked)}
            />
            Tanılama ayrıntılarını göster
          </label>
        </section>
      </div>
      <div className="save-bar">
        <span>Ayarlar uygulama yeniden başlatıldığında korunur.</span>
        <button
          className="button primary"
          disabled={busy}
          onClick={() => void save()}
        >
          <Check size={17} />
          {busy ? "Kaydediliyor…" : "Ayarları kaydet"}
        </button>
      </div>
    </>
  );
}
