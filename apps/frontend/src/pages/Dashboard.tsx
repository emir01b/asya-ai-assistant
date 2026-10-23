import { useEffect, useState } from "react";
import { AudioLines, ArrowRight, MessageCircle, Mic } from "lucide-react";
import { api, audioUrl, date, statusLabel } from "../api";
import { Empty, Stat, StatusRow, type Feedback } from "../components/ui";
import type { SystemStatus, GPU, Job, Conversation } from "../types";
import { type Page } from "../catalog";

export default function Dashboard({
  system,
  gpu,
  navigate,
  fail,
}: {
  system: SystemStatus | null;
  gpu: GPU | null;
  navigate: (p: Page) => void;
  fail: Feedback["fail"];
}) {
  const [recent, setRecent] = useState<Job[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  useEffect(() => {
    void api<Job[]>("/tts/history")
      .then((v) => setRecent(v.slice(0, 3)))
      .catch(fail);
    void api<Conversation[]>("/conversations")
      .then((v) => setConversations(v.slice(0, 4)))
      .catch(fail);
  }, [fail]);
  return (
    <>
      <div className="stats-grid">
        <Stat
          label="Ses üretimi"
          value={String(system?.counts.generations ?? "—")}
          detail="Kalıcı üretim kayıtları"
        />
        <Stat
          label="Ses profili"
          value={String(system?.counts.voices ?? "—")}
          detail="Kişisel ses kütüphaneniz"
        />
        <Stat
          label="Konuşma"
          value={String(system?.counts.conversations ?? "—")}
          detail="Yerel sohbet geçmişi"
        />
        <Stat
          label="GPU belleği"
          value={
            gpu?.available
              ? `${((gpu.used_mb || 0) / 1024).toFixed(1)} GB`
              : "—"
          }
          detail={
            gpu?.available
              ? `${((gpu.total_mb || 0) / 1024).toFixed(1)} GB toplam VRAM`
              : "GPU bilgisi alınamadı"
          }
        />
      </div>
      <div className="two-cols">
        <section className="panel padded">
          <h2>Model ve servisler</h2>
          <StatusRow
            label="LM Studio"
            good={!!system?.lm.connected}
            value={
              system?.lm.connected
                ? system.lm.models.length + " model mevcut"
                : "Bağlı değil"
            }
          />
          <StatusRow
            label="Chatterbox V3"
            good={!!system?.tts.loaded}
            value={
              system?.tts.loaded ? "Bellekte hazır" : "İlk üretimde yüklenir"
            }
          />
          <StatusRow
            label="Whisper STT"
            good={!!system?.stt.installed}
            value={
              system?.stt.installed ? "İzole ortam hazır" : "Kurulum gerekli"
            }
          />
          <StatusRow
            label="Üretim kuyruğu"
            good={!system?.tts.pending}
            value={`${system?.tts.pending ?? 0} bekleyen görev`}
          />
          <button
            className="button secondary"
            onClick={() => navigate("settings")}
          >
            Servis ayarları <ArrowRight size={16} />
          </button>
        </section>
        <section className="panel quick-start">
          <div className="eyebrow">BİR FİKİRDEN BİR SESE</div>
          <h2>
            Bir sonraki hikâyeniz
            <br />
            burada başlıyor.
          </h2>
          <p>
            Türkçe ses üretin, kendi sesinizi klonlayın veya yerel asistanınızla
            konuşun.
          </p>
          <div className="inline">
            <button
              className="button primary"
              onClick={() => navigate("studio")}
            >
              <AudioLines size={17} />
              Ses oluştur
            </button>
            <button
              className="button secondary"
              onClick={() => navigate("chat")}
            >
              <Mic size={17} />
              Sohbet et
            </button>
          </div>
        </section>
      </div>
      <div className="section-heading">
        <h2>Son üretimler</h2>
        <button className="text-link" onClick={() => navigate("history")}>
          Tüm geçmiş <ArrowRight size={14} />
        </button>
      </div>
      {recent.length ? (
        recent.map((j) => (
          <div className="list-row" key={j.id}>
            <AudioLines size={22} />
            <div>
              <strong>{j.text.slice(0, 90)}</strong>
              <p>
                {date(j.created_at)} · {statusLabel[j.status]}
              </p>
            </div>
            {j.asset_id && <audio controls src={audioUrl(j.asset_id)} />}
          </div>
        ))
      ) : (
        <Empty
          title="İlk sesinizi oluşturun"
          description="Yeni üretimleriniz burada görünecek."
        />
      )}
      <div className="section-heading">
        <h2>Son konuşmalar</h2>
      </div>
      {conversations.length ? (
        conversations.map((c) => (
          <div key={c.id} className="list-row">
            <MessageCircle size={20} />
            <div>
              <strong>{c.title}</strong>
              <p>
                {c.message_count} mesaj · {date(c.created_at)}
              </p>
            </div>
            <button className="text-link" onClick={() => navigate("chat")}>
              Sohbete git <ArrowRight size={14} />
            </button>
          </div>
        ))
      ) : (
        <Empty
          title="Henüz konuşma yok"
          description="Sesli sohbet sayfasından bir konuşma başlatın."
        />
      )}
    </>
  );
}
