import { useState, useEffect, useCallback } from "react";
import { FlaskConical, LoaderCircle, Mic, RefreshCw } from "lucide-react";
import { api, date, seconds } from "../api";
import {
  Tag,
  Stat,
  LanguageSelect,
  Empty,
  type Feedback,
} from "../components/ui";
import type { GPU, Diagnostics, Transcript, Job } from "../types";

export default function DiagnosticsPage({
  gpu,
  fail,
  notify,
  debug,
}: { gpu: GPU | null; debug: boolean } & Feedback) {
  const [data, setData] = useState<Diagnostics | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [language, setLanguage] = useState("tr");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(
    () => api<Diagnostics>("/diagnostics").then(setData).catch(fail),
    [fail],
  );
  useEffect(() => {
    void refresh();
  }, [refresh]);
  async function transcribe() {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    setBusy(true);
    try {
      const result = await api<Transcript>("/stt/transcribe", {
        method: "POST",
        body: form,
      });
      setTranscript(result);
      if (result.warning) fail(new Error(result.warning));
      await refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  const latest = data?.benchmarks.find((b) => b.source === "tts");
  const chat = data?.benchmarks.find((b) => b.source === "chat");
  const stt = data?.benchmarks.find((b) => b.source === "stt");
  return (
    <>
      {debug && (
        <details className="panel padded">
          <summary>Gelişmiş tanılama ayrıntıları</summary>
          <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {JSON.stringify({ gpu, tts: data?.tts }, null, 2)}
          </pre>
        </details>
      )}
      <div className="toolbar">
        <Tag good={!!gpu?.available}>{gpu?.name || "GPU okunamadı"}</Tag>
        <button className="button secondary" onClick={() => void refresh()}>
          <RefreshCw size={15} />
          Yenile
        </button>
        <button
          className="button secondary"
          onClick={() =>
            void api<Job>("/tts/warmup", { method: "POST" })
              .then((j) =>
                notify(
                  `Isınma üretimi kuyruğa alındı: ${j.id.slice(0, 8)}. Geçmiş’ten izleyebilirsiniz.`,
                ),
              )
              .catch(fail)
          }
        >
          <FlaskConical size={15} />
          TTS benchmark
        </button>
      </div>
      <div className="stats-grid">
        <Stat
          label="TTS ilk ses"
          value={seconds(latest?.first_audio_seconds)}
          detail="İstek → ilk hazır segment"
        />
        <Stat
          label="TTS RTF"
          value={latest?.rtf?.toFixed(3) || "Ölçülmedi"}
          detail="Üretim süresi / ses süresi"
        />
        <Stat
          label="LLM ilk token"
          value={seconds(chat?.llm_first_token_seconds)}
          detail="İstek → ilk metin parçası"
        />
        <Stat
          label="STT süresi"
          value={seconds(stt?.seconds)}
          detail={stt?.device || "Henüz STT çalışmadı"}
        />
      </div>
      <section className="panel padded">
        <h2>STT dosya testi</h2>
        <p className="help-text">
          0,25–120 saniyelik ses yükleyin. Model, cihaz, süre ve zaman
          damgalarını doğrulayın.
        </p>
        <div className="toolbar">
          <input
            aria-label="Transkripsiyon dosyası"
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <LanguageSelect value={language} onChange={setLanguage} auto />
          <button
            className="button primary"
            disabled={!file || busy}
            onClick={() => void transcribe()}
          >
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Mic size={16} />
            )}
            Yazıya dönüştür
          </button>
        </div>
        {transcript && (
          <div className="transcript">
            <strong>{transcript.text || "Konuşma bulunamadı."}</strong>
            <p>
              {seconds(transcript.seconds)} · {transcript.device} ·{" "}
              {transcript.language}
            </p>
            {transcript.segments.map((s, i) => (
              <p key={i}>
                <code>
                  {s.start.toFixed(1)}–{s.end.toFixed(1)}
                </code>{" "}
                {s.text}
              </p>
            ))}
          </div>
        )}
      </section>
      <div className="section-heading">
        <h2>Gerçek ölçüm kayıtları</h2>
        <span className="muted">En son 200 ölçüm</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tarih</th>
              <th>Kaynak</th>
              <th>Toplam</th>
              <th>İlk ses</th>
              <th>RTF</th>
              <th>Tepe VRAM</th>
            </tr>
          </thead>
          <tbody>
            {data?.benchmarks.map((b) => (
              <tr key={b.id}>
                <td>{date(b.created_at)}</td>
                <td>{b.source}</td>
                <td>{seconds(b.total_seconds ?? b.seconds)}</td>
                <td>{seconds(b.first_audio_seconds)}</td>
                <td>{b.rtf?.toFixed(3) || "—"}</td>
                <td>
                  {b.peak_vram_mb ? `${b.peak_vram_mb.toFixed(0)} MB` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data?.benchmarks.length && (
          <Empty
            title="Henüz ölçüm yok"
            description="Bir üretim veya konuşma tamamlandığında gerçek sonuçlar burada listelenir."
          />
        )}
      </div>
      <div className="section-heading">
        <h2>Hata geçmişi</h2>
      </div>
      {data?.errors.map((e) => (
        <div className="error-record" key={e.id}>
          <span>
            {e.source} · {date(e.created_at)}
          </span>
          <p>{e.message}</p>
        </div>
      ))}
      {!data?.errors.length && <p className="muted">Kaydedilmiş hata yok.</p>}
    </>
  );
}
