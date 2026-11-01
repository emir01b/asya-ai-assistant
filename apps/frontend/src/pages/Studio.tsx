import { useEffect, useRef, useState } from "react";
import {
  AudioLines,
  ArrowRight,
  CircleHelp,
  Cpu,
  LoaderCircle,
  SlidersHorizontal,
  Square,
  Volume2,
  WandSparkles,
  X,
} from "lucide-react";
import { api, seconds, statusLabel, generateAudio } from "../api";
import {
  IconButton,
  Tag,
  LanguageSelect,
  VoiceSelect,
  Player,
  Range,
  type Feedback,
} from "../components/ui";
import type { Voice, Settings, Job } from "../types";
import { presets } from "../catalog";
import GenerationDetails from "../components/GenerationDetails";

export default function Studio({
  voices,
  settings,
  reuse,
  refresh,
  fail,
  notify,
}: {
  voices: Voice[];
  settings: Settings | null;
  reuse: Job | null;
  refresh: () => Promise<void>;
} & Feedback) {
  const [text, setText] = useState("");
  const [voice, setVoice] = useState("");
  const [language, setLanguage] = useState("tr");
  const [exaggeration, setExaggeration] = useState(0.5);
  const [cfg, setCfg] = useState(0.5);
  const [preset, setPreset] = useState("Normal");
  const [job, setJob] = useState<Job | null>(null);
  const [comparison, setComparison] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [speechQuality, setSpeechQuality] =
    useState<Settings["speech_quality"]>("balanced");
  const [compareCandidates, setCompareCandidates] = useState(false);
  const [seed, setSeed] = useState<number | null>(null);
  const [speechRate, setSpeechRate] = useState(1);
  const [preview, setPreview] = useState<string | null>(null);
  const initializedProfile = useRef<string | null>(null);
  useEffect(() => {
    if (settings) {
      setVoice(settings.default_voice);
      setLanguage(settings.language);
    }
  }, [settings?.default_voice, settings?.language]);
  useEffect(() => {
    const id = settings?.default_voice ?? "";
    if (reuse || initializedProfile.current === id) return;
    const selected = voices.find((v) => v.id === id);
    if (id && !selected) return;
    initializedProfile.current = id;
    setExaggeration(selected?.exaggeration ?? 0.5);
    setCfg(selected?.cfg_weight ?? 0.5);
  }, [settings?.default_voice, voices, reuse]);
  useEffect(() => {
    setSpeechQuality(settings?.speech_quality ?? "balanced");
    setCompareCandidates(settings?.compare_candidates ?? false);
  }, [settings?.speech_quality, settings?.compare_candidates]);
  useEffect(() => {
    if (reuse) {
      setText(reuse.text);
      setVoice(reuse.voice_id || "");
      setLanguage(reuse.language);
      setExaggeration(reuse.exaggeration);
      setCfg(reuse.cfg_weight);
      setSpeechQuality(reuse.speech_quality ?? "balanced");
      setCompareCandidates(reuse.compare_candidates ?? false);
      setSeed(reuse.seed ?? null);
      setSpeechRate(reuse.speech_rate ?? 1);
    }
  }, [reuse]);
  const active =
    !!job && ["queued", "running", "cancelling"].includes(job.status);
  useEffect(() => {
    if (!active || !job) return;
    let mounted = true;
    const timer = window.setInterval(() => {
      void api<Job>(`/tts/jobs/${job.id}`)
        .then((v) => {
          if (mounted) {
            setJob(v);
            if (v.status === "failed") fail(v.error);
          }
        })
        .catch(fail);
    }, 600);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [active, job?.id, fail]);
  async function generate() {
    if (!text.trim()) {
      fail(new Error("Seslendirmek için metin girin."));
      return;
    }
    setSubmitting(true);
    try {
      if (job?.asset_id) setComparison(job);
      setJob(
        await generateAudio({
          text,
          voice_id: voice || null,
          language,
          exaggeration,
          cfg_weight: cfg,
          provider: "chatterbox",
          speech_quality: speechQuality,
          compare_candidates: compareCandidates,
          seed,
          speech_rate: speechRate,
        }),
      );
    } catch (e) {
      fail(e);
    } finally {
      setSubmitting(false);
    }
  }
  const chooseVoice = (id: string) => {
    setVoice(id);
    const selected = voices.find((v) => v.id === id);
    if (selected) {
      setExaggeration(selected.exaggeration);
      setCfg(selected.cfg_weight);
      setLanguage(selected.language);
    }
  };
  async function saveProfile() {
    const selected = voices.find((v) => v.id === voice);
    if (!selected) return;
    setSavingProfile(true);
    try {
      await api(`/voices/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: selected.name,
          language: selected.language,
          exaggeration,
          cfg_weight: cfg,
        }),
      });
      await refresh();
      notify(
        "İfade ve CFG ses profiline kaydedildi. Yeni üretimlerde uygulanır.",
      );
    } catch (e) {
      fail(e);
    } finally {
      setSavingProfile(false);
    }
  }
  return (
    <>
      <div className="studio-grid">
        <section className="panel editor-panel">
          <div className="panel-heading">
            <h2>
              <span className="step">01</span>Metniniz
            </h2>
            <span className="muted">Bir fikir, bin farklı ton.</span>
          </div>
          <textarea
            className="script-editor"
            aria-label="Seslendirilecek metin"
            placeholder={
              "Bir hikâye anlatın. Bir fikre hayat verin.\n\nSeslendirmek istediğiniz metni buraya yazın…"
            }
            value={text}
            maxLength={12000}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="editor-bottom">
            <span>{text.length.toLocaleString("tr-TR")} / 12.000 karakter</span>
            <button
              className="text-link"
              onClick={() =>
                setText(
                  "Merhaba! Bazen bir ses, bin kelimeden daha fazlasını anlatır. Bugün kendi hikâyenize hayat vermenin tam zamanı.",
                )
              }
              disabled={active}
            >
              Örnek metin <ArrowRight size={14} />
            </button>
          </div>
          <div className="editor-hint">
            <CircleHelp size={15} />
            Noktalama işaretleri, doğal duraklamalar ve daha iyi bir anlatım
            sağlar.
          </div>
        </section>
        <section className="panel controls-panel">
          <div className="panel-heading">
            <h2>
              <span className="step">02</span>Ses tasarımı
            </h2>
            <SlidersHorizontal size={17} />
          </div>
          <label>SES PROFİLİ</label>
          <VoiceSelect voices={voices} value={voice} onChange={chooseVoice} />
          {voice && (
            <button
              className="text-link preview-link"
              onClick={() =>
                setPreview(
                  voices.find((v) => v.id === voice)?.reference_asset_id ||
                    voices.find((v) => v.id === voice)?.asset_id ||
                    null,
                )
              }
            >
              <Volume2 size={14} />
              Referansı dinle
            </button>
          )}
          <label>DİL</label>
          <LanguageSelect value={language} onChange={setLanguage} />
          <div className="control-divider" />
          <label>
            İFADE PROFİLİ <span className="small-tag">DENEYSEL</span>
          </label>
          <div className="preset-grid">
            {presets.map(([name, e, c]) => (
              <button
                key={name}
                className={preset === name ? "selected" : ""}
                onClick={() => {
                  setPreset(name);
                  setExaggeration(e);
                  setCfg(c);
                }}
              >
                {name}
              </button>
            ))}
          </div>
          <p className="help-text">
            Profiller ifade yoğunluğunu ve CFG değerini ayarlar. Belirli bir
            duyguyu garanti etmez.
          </p>
          <Range
            label="İfade yoğunluğu"
            value={exaggeration}
            max={2}
            onChange={(v) => {
              setExaggeration(v);
              setPreset("Özel");
            }}
          />
          <Range
            label="CFG ağırlığı"
            value={cfg}
            onChange={(v) => {
              setCfg(v);
              setPreset("Özel");
            }}
          />
          <p className="help-text">
            İfade anlatım yoğunluğunu, CFG metne ve referansa yönlendirmeyi
            etkiler; ses perdesi veya üretim kalitesi ayarı değildir.
            Değişiklikler yalnızca yeni üretimlere uygulanır. Kaydetmek mevcut
            ses dosyalarını değiştirmez.
          </p>
          <button
            className="button secondary"
            disabled={!voice || savingProfile}
            onClick={() => void saveProfile()}
          >
            {savingProfile
              ? "Kaydediliyor…"
              : "İfade ve CFG’yi seçili profile kaydet"}
          </button>
          <div className="control-divider" />
          <p className="help-text">
            Üretim:{" "}
            {speechQuality === "quality"
              ? "Kalite (deneysel)"
              : speechQuality === "fast"
                ? "Hızlı"
                : "Dengeli"}
            {compareCandidates
              ? " · İki aday (yaklaşık iki kat hesaplama)"
              : " · Tek aday"}
            . Varsayılanları Ayarlar → Ses ve Konuşma bölümünden
            değiştirebilirsiniz.
          </p>
          <Range
            label="Stüdyo konuşma hızı"
            value={speechRate}
            min={0.75}
            max={1.15}
            step={0.05}
            onChange={setSpeechRate}
          />
          <p className="help-text">
            Tempo ayrı uygulanır; 1,00× modelin doğal hızıdır.
          </p>
          <label htmlFor="generation-seed">SEED (İSTEĞE BAĞLI)</label>
          <input
            id="generation-seed"
            type="number"
            min={0}
            max={4294967295}
            value={seed ?? ""}
            placeholder="Rastgele"
            onChange={(e) =>
              setSeed(e.target.value === "" ? null : Number(e.target.value))
            }
          />
          <div className="model-box">
            <span className="model-icon">
              <Cpu size={18} />
            </span>
            <div>
              <strong>Chatterbox Multilingual V3</strong>
              <p>
                Yerel TTS motoru ·{" "}
                {settings?.tts_device.toUpperCase() || "CUDA"}
              </p>
            </div>
            <Tag good>Aktif</Tag>
          </div>
        </section>
      </div>
      <div className="generate-bar">
        <div>
          <WandSparkles size={18} />
          <span>
            {active
              ? statusLabel[job.status]
              : "Metninizi duymaya hazır mısınız?"}
            <small>
              {active
                ? "İlk segment hazır olduğunda aşağıdan dinleyebilirsiniz."
                : "Ses üretimi cihazınızda gerçekleşir."}
            </small>
          </span>
        </div>
        <div className="inline">
          {active && (
            <button
              className="button secondary"
              onClick={() =>
                void api<Job>(`/tts/jobs/${job.id}/cancel`, { method: "POST" })
                  .then(setJob)
                  .catch(fail)
              }
              disabled={job.status === "cancelling"}
            >
              <Square size={14} />
              İptal
            </button>
          )}
          <button
            aria-label="Ses oluştur"
            className="button primary"
            disabled={active || submitting || !text.trim()}
            onClick={() => void generate()}
          >
            {active || submitting ? (
              <LoaderCircle className="spin" size={18} />
            ) : (
              <AudioLines size={18} />
            )}
            Ses oluştur <span>↗</span>
          </button>
        </div>
      </div>
      {active && (
        <div
          className="progress"
          role="progressbar"
          aria-label="Üretim ilerlemesi"
          aria-valuenow={Math.round(job.progress * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <i style={{ width: `${Math.max(3, job.progress * 100)}%` }} />
        </div>
      )}
      <div className="section-heading">
        <h2>Ses çıktısı</h2>
        <span className="muted">
          {job ? statusLabel[job.status] : "Henüz bir üretim yok"}
        </span>
      </div>
      {job && (
        <GenerationDetails
          job={job}
          fail={fail}
          onSelect={setJob}
          output={settings?.output_id}
        />
      )}
      {job?.asset_id ? (
        <>
          <Player asset={job.asset_id} output={settings?.output_id} />
          <div className="metric-row">
            <span>
              Ses süresi <b>{seconds(job.metrics.duration)}</b>
            </span>
            <span>
              Üretim <b>{seconds(job.metrics.total_seconds)}</b>
            </span>
            <span>
              İlk segment <b>{seconds(job.metrics.first_audio_seconds)}</b>
            </span>
            <span>
              RTF <b>{job.metrics.rtf?.toFixed(2)}</b>
            </span>
            <button
              className="text-link"
              onClick={() => {
                setComparison(job);
                notify(
                  "Bu çıktı A/B karşılaştırması için A olarak kaydedildi. Yeni bir üretim yapın.",
                );
              }}
            >
              A olarak işaretle
            </button>
          </div>
        </>
      ) : job?.segments.length ? (
        <div className="segment-list">
          {job.segments.map((s) => (
            <Player
              key={s.asset_id}
              asset={s.asset_id}
              label={`Segment ${s.index + 1} · ${s.text}`}
            />
          ))}
        </div>
      ) : (
        <div className="output-placeholder">
          <div className="empty-wave">
            <AudioLines size={34} />
          </div>
          <div>
            <h3>
              {job?.status === "failed"
                ? "Üretim tamamlanamadı"
                : "Sesiniz burada hayat bulacak."}
            </h3>
            <p>
              {job?.error ||
                "Metninizi ve ses profilinizi seçerek ilk kaydınızı oluşturun."}
            </p>
          </div>
        </div>
      )}
      {comparison?.asset_id && job?.asset_id && comparison.id !== job.id && (
        <div className="panel compare">
          <h2>A/B karşılaştırması</h2>
          <div className="two-cols">
            <Player
              asset={comparison.asset_id}
              label={`A · İfade ${comparison.exaggeration} / CFG ${comparison.cfg_weight}`}
            />
            <Player
              asset={job.asset_id}
              label={`B · İfade ${job.exaggeration} / CFG ${job.cfg_weight}`}
            />
          </div>
        </div>
      )}
      {preview && (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <IconButton
              label="Önizlemeyi kapat"
              onClick={() => setPreview(null)}
            >
              <X size={18} />
            </IconButton>
            <Player asset={preview} label="Referans ses" />
          </div>
        </div>
      )}
    </>
  );
}
