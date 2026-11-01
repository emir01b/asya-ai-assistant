import { useState } from "react";
import { api, audioUrl } from "../api";
import type { Job } from "../types";
import { Player, type Feedback } from "./ui";

export default function GenerationDetails({
  job,
  onSelect,
  fail,
  output,
}: {
  job: Job;
  onSelect: (job: Job) => void;
  fail: Feedback["fail"];
  output?: string;
}) {
  const [selecting, setSelecting] = useState(false);
  const quality = job.speech_quality ?? "balanced";
  const candidates = job.candidates ?? [];
  const comparison = job.compare_candidates || candidates.length > 1;
  const snapshot = job.voice_snapshot;
  async function select(index: number) {
    setSelecting(true);
    try {
      onSelect(
        await api<Job>(`/tts/history/${job.id}/select-candidate`, {
          method: "POST",
          body: JSON.stringify({ index }),
        }),
      );
    } catch (error) {
      fail(error);
    } finally {
      setSelecting(false);
    }
  }
  return (
    <div className="generation-details">
      <p className="help-text">
        Etkin ayarlar · İfade {job.exaggeration} · CFG {job.cfg_weight} · Tempo{" "}
        {job.speech_rate ?? 1}×{" · "}Üretim{" "}
        {quality === "quality"
          ? "Kalite (deneysel)"
          : quality === "fast"
            ? "Hızlı"
            : "Dengeli"}
        {" · "}Seed {job.seed ?? "Kaydedilmedi (eski kayıt)"}
        {" · "}Model {job.model ?? job.provider}
        {snapshot?.name && <> · Profil {snapshot.name}</>}
        {snapshot?.reference_start != null &&
          snapshot?.reference_end != null && (
            <>
              {" "}
              · Referans aralığı {snapshot.reference_start.toFixed(2)}–
              {snapshot.reference_end.toFixed(2)} sn
            </>
          )}
        {" · "}Referans{" "}
        {job.reference_asset_id ? (
          <a
            href={audioUrl(job.reference_asset_id)}
            target="_blank"
            rel="noreferrer"
          >
            Kullanılan klibi dinle
          </a>
        ) : (
          "Yok / eski kayıtta belirtilmemiş"
        )}
      </p>
      {comparison && (
        <section className="panel padded" aria-label="Üretim adayları">
          <h3>Üretim adayları A/B</h3>
          <p className="help-text">
            İki adayı dinleyin ve tercihinizi kaydedin. Otomatik değerlendirme
            dinleme kalitesini garanti etmez.
          </p>
          {!!job.candidate_errors?.length && (
            <ul className="error-text" aria-label="Aday üretim uyarıları">
              {job.candidate_errors.map((error, index) => (
                <li key={index}>
                  Seed {error.seed}: {error.error}
                </li>
              ))}
            </ul>
          )}
          {job.status === "completed" && candidates.length < 2 && (
            <p className="help-text">
              Karşılaştırma için yalnızca {candidates.length} aday hazır. İkinci
              aday üretilememiş olabilir.
            </p>
          )}
          <div className="two-cols">
            {candidates.map((candidate, position) => {
              const index =
                typeof candidate.index === "number"
                  ? candidate.index
                  : position;
              if (typeof candidate.asset_id !== "string") return null;
              const label = String.fromCharCode(65 + position);
              return (
                <div key={index}>
                  <Player
                    asset={candidate.asset_id}
                    label={`Aday ${label}`}
                    output={output}
                  />
                  <p className="help-text">
                    Seed{" "}
                    {typeof candidate.seed === "number"
                      ? candidate.seed
                      : "Kaydedilmedi"}
                  </p>
                  {candidate.scoring?.error && (
                    <p className="error-text">
                      Değerlendirme yapılamadı: {candidate.scoring.error}
                    </p>
                  )}
                  {candidate.scoring?.fidelity != null ? (
                    <p className="help-text">
                      Metin uyumu: %
                      {(candidate.scoring.fidelity * 100).toFixed(0)} · Ses
                      benzerliği:{" "}
                      {candidate.scoring.speaker_similarity == null
                        ? "Ölçülemedi"
                        : `%${(candidate.scoring.speaker_similarity * 100).toFixed(0)}`}
                    </p>
                  ) : (
                    <p className="help-text">
                      Otomatik metin uyumu / ses benzerliği değerlendirmesi yok.
                    </p>
                  )}
                  <button
                    className="button secondary"
                    disabled={
                      selecting ||
                      job.status !== "completed" ||
                      job.selected_candidate === index
                    }
                    onClick={() => void select(index)}
                  >
                    {job.selected_candidate === index
                      ? `Aday ${label} seçili`
                      : `Aday ${label} seç`}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
