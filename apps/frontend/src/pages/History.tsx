import { useState, useEffect, useCallback } from "react";
import { RefreshCw, Trash2, ArrowDownToLine } from "lucide-react";
import { api, audioUrl, date, seconds, statusLabel } from "../api";
import {
  IconButton,
  Tag,
  Player,
  Empty,
  type Feedback,
} from "../components/ui";
import type { Voice, Job } from "../types";
import { languageNames } from "../catalog";

export default function History({
  voices,
  fail,
  rerun,
}: {
  voices: Voice[];
  fail: Feedback["fail"];
  rerun: (j: Job) => void;
}) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const load = useCallback(
    () => api<Job[]>("/tts/history").then(setJobs).catch(fail),
    [fail],
  );
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <>
      <div className="toolbar">
        <input
          aria-label="Geçmişte ara"
          placeholder="Metin içinde ara…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <IconButton label="Geçmişi yenile" onClick={() => void load()}>
          <RefreshCw size={17} />
        </IconButton>
      </div>
      {selected.length === 2 && (
        <div className="panel padded">
          <h2>A/B karşılaştırması</h2>
          <div className="two-cols">
            {selected.map((id, i) => {
              const j = jobs.find((j) => j.id === id)!;
              return (
                <Player
                  key={id}
                  asset={j.asset_id!}
                  label={`${i === 0 ? "A" : "B"} · İfade ${j.exaggeration} / CFG ${j.cfg_weight}`}
                />
              );
            })}
          </div>
        </div>
      )}
      <div className="history-list">
        {jobs
          .filter((j) =>
            j.text
              .toLocaleLowerCase("tr-TR")
              .includes(search.toLocaleLowerCase("tr-TR")),
          )
          .map((j) => (
            <article className="panel history-card" key={j.id}>
              <div className="history-head">
                <Tag good={j.status === "completed"}>
                  {statusLabel[j.status]}
                </Tag>
                <span>{date(j.created_at)}</span>
              </div>
              <h3>{j.text}</h3>
              <p>
                Chatterbox V3 · {languageNames[j.language]} ·{" "}
                {voices.find((v) => v.id === j.voice_id)?.name ||
                  "Varsayılan / eski profil"}{" "}
                · İfade {j.exaggeration} · CFG {j.cfg_weight}
              </p>
              {j.asset_id && <audio controls src={audioUrl(j.asset_id)} />}
              <div className="history-actions">
                <span>
                  {seconds(j.metrics.duration)} ses ·{" "}
                  {seconds(j.metrics.total_seconds)} üretim · RTF{" "}
                  {j.metrics.rtf?.toFixed(2) || "—"}
                </span>
                <div className="inline">
                  {j.asset_id && (
                    <button
                      className={`text-link ${selected.includes(j.id) ? "accent" : ""}`}
                      onClick={() =>
                        setSelected((v) =>
                          v.includes(j.id)
                            ? v.filter((id) => id !== j.id)
                            : [...v.slice(-1), j.id],
                        )
                      }
                    >
                      A/B seç
                    </button>
                  )}
                  <button className="text-link" onClick={() => rerun(j)}>
                    Yeniden üret
                  </button>
                  {j.asset_id && (
                    <a
                      className="text-link"
                      href={audioUrl(j.asset_id)}
                      download
                    >
                      <ArrowDownToLine size={14} />
                      WAV
                    </a>
                  )}
                  <IconButton
                    label="Üretimi sil"
                    onClick={() =>
                      void api(`/tts/history/${j.id}`, { method: "DELETE" })
                        .then(() => {
                          setSelected((v) => v.filter((id) => id !== j.id));
                          return load();
                        })
                        .catch(fail)
                    }
                  >
                    <Trash2 size={15} />
                  </IconButton>
                </div>
              </div>
              {j.error && <p className="error-text">{j.error}</p>}
            </article>
          ))}
      </div>
      {!jobs.length && (
        <Empty
          title="Henüz bir üretim yok"
          description="Ses Stüdyosu’ndan oluşturduğunuz sesler burada saklanır."
        />
      )}
    </>
  );
}
