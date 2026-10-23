import { useState } from "react";
import {
  Plus,
  Upload,
  ShieldCheck,
  AudioLines,
  LoaderCircle,
  Trash2,
} from "lucide-react";
import { api, audioUrl } from "../api";
import { Tag, IconButton, Empty, type Feedback } from "../components/ui";
import type { Voice, Settings } from "../types";
import { languageNames } from "../catalog";

export default function Library({
  voices,
  settings,
  refresh,
  fail,
  notify,
}: {
  voices: Voice[];
  settings: Settings | null;
  refresh: () => Promise<void>;
} & Feedback) {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  async function upload() {
    if (!file || !name.trim() || !consent) {
      fail(new Error("Ad, referans dosyası ve kullanım izni gerekli."));
      return;
    }
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    form.append("consent", "true");
    form.append("language", "tr");
    try {
      await api("/voices", { method: "POST", body: form });
      setName("");
      setFile(null);
      setConsent(false);
      await refresh();
      notify("Ses profili kaydedildi.");
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel padded">
        <div className="section-heading">
          <h2>
            <Plus size={18} />
            Yeni ses profili
          </h2>
          <span className="muted">0,25–60 saniye · En fazla 25 MB</span>
        </div>
        <div className="two-cols">
          <div>
            <label htmlFor="voice-name">PROFİL ADI</label>
            <input
              id="voice-name"
              value={name}
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
              placeholder="Örn. Anlatıcı sesim"
            />
            <label className="upload-zone">
              <Upload size={25} />
              <strong>{file?.name || "Referans ses dosyası seçin"}</strong>
              <span>WAV, MP3, M4A, WebM · İçerik doğrulanır</span>
              <input
                aria-label="Referans ses dosyası"
                type="file"
                accept="audio/*,video/mp4"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>
          <div className="consent-card">
            <ShieldCheck size={25} />
            <h3>Sesinizin kontrolü sizde.</h3>
            <p>
              Yalnızca size ait veya kullanma izniniz olan sesleri yükleyin.
              Referanslar bu cihazda saklanır.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              Bu sesin hak sahibiyim veya kullanım iznim var.
            </label>
            <button
              className="button primary"
              disabled={busy || !file || !name.trim() || !consent}
              onClick={() => void upload()}
            >
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Plus size={16} />
              )}
              Profili oluştur
            </button>
          </div>
        </div>
      </section>
      <div className="section-heading">
        <h2>
          Sesleriniz <span className="small-tag">{voices.length}</span>
        </h2>
      </div>
      <div className="voice-grid">
        {voices.map((v) => (
          <article className="panel voice-card" key={v.id}>
            <div className="voice-card-head">
              <div className="voice-symbol">
                <AudioLines size={25} />
              </div>
              {settings?.default_voice === v.id && <Tag good>Varsayılan</Tag>}
            </div>
            {editing === v.id ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void api(`/voices/${v.id}`, {
                    method: "PUT",
                    body: JSON.stringify({ ...v, name: editName }),
                  })
                    .then(() => {
                      setEditing(null);
                      return refresh();
                    })
                    .catch(fail);
                }}
              >
                <input
                  aria-label="Yeni profil adı"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  maxLength={80}
                  required
                />
                <button className="text-link">Kaydet</button>
                <button
                  type="button"
                  className="text-link"
                  onClick={() => setEditing(null)}
                >
                  Vazgeç
                </button>
              </form>
            ) : (
              <h3>{v.name}</h3>
            )}
            <p>
              {languageNames[v.language]} · {v.duration.toFixed(1)} sn ·{" "}
              {v.sample_rate / 1000} kHz
            </p>
            <audio controls src={audioUrl(v.asset_id)} />
            <div className="voice-actions">
              <button
                className="text-link"
                onClick={() => {
                  setEditing(v.id);
                  setEditName(v.name);
                }}
              >
                Adı düzenle
              </button>
              <button
                className="text-link"
                disabled={!settings || settings.default_voice === v.id}
                onClick={() =>
                  void api("/settings", {
                    method: "PUT",
                    body: JSON.stringify({ ...settings, default_voice: v.id }),
                  })
                    .then(refresh)
                    .catch(fail)
                }
              >
                Varsayılan yap
              </button>
              <IconButton
                label={`${v.name} profilini sil`}
                onClick={() =>
                  void api(`/voices/${v.id}`, { method: "DELETE" })
                    .then(refresh)
                    .catch(fail)
                }
              >
                <Trash2 size={15} />
              </IconButton>
            </div>
          </article>
        ))}
      </div>
      {!voices.length && (
        <Empty
          title="Kütüphaneniz sizi bekliyor"
          description="İlk referans sesinizi yükleyerek başlayın."
        />
      )}
    </>
  );
}
