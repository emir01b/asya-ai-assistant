import { useState, useEffect, useCallback } from "react";
import {
  AudioLines,
  Check,
  ChevronRight,
  CircleHelp,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "./api";
import { IconButton, Tag, Empty } from "./components/ui";
import { pages, titleMap, type Page } from "./catalog";
import type { GPU, Job, Settings, SystemStatus, Voice } from "./types";
import Studio from "./pages/Studio";
import Dashboard from "./pages/Dashboard";
import Library from "./pages/Library";
import History from "./pages/History";
import VoiceChat from "./pages/VoiceChat";
import SettingsPage from "./pages/SettingsPage";
import DiagnosticsPage from "./pages/DiagnosticsPage";

export default function App() {
  const [page, setPage] = useState<Page>("studio");
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [gpu, setGpu] = useState<GPU | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reuse, setReuse] = useState<Job | null>(null);
  const notify = useCallback((s: string) => {
    setNotice(s);
    window.setTimeout(() => setNotice(""), 5000);
  }, []);
  const fail = useCallback(
    (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    [],
  );
  const refresh = useCallback(async () => {
    await Promise.allSettled([
      api<SystemStatus>("/system/status").then(setSystem).catch(fail),
      api<GPU>("/system/gpu").then(setGpu).catch(fail),
      api<Voice[]>("/voices").then(setVoices).catch(fail),
      api<Settings>("/settings").then(setSettings).catch(fail),
    ]);
  }, [fail]);
  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => {
      void Promise.all([
        api<SystemStatus>("/system/status").then(setSystem),
        api<GPU>("/system/gpu").then(setGpu),
      ]).catch(() => {});
    }, 15000);
    return () => clearInterval(id);
  }, [refresh]);
  const navigate = (p: Page) => {
    setPage(p);
    setError("");
  };
  const rerun = (job: Job) => {
    setReuse(job);
    navigate("studio");
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            navigate("dashboard");
          }}
        >
          <div className="brand-icon">
            <AudioLines size={24} />
          </div>
          <div>
            ASYA<span>YEREL SESLİ ASİSTAN</span>
          </div>
        </a>
        <div className="workspace-label">KİŞİSEL ÇALIŞMA ALANI</div>
        <nav aria-label="Ana menü">
          {pages.map(([id, label, Icon], i) => (
            <button
              key={id}
              className={`${page === id ? "active" : ""} ${i === 5 ? "nav-separated" : ""}`}
              onClick={() => navigate(id)}
            >
              <Icon size={19} />
              {label}
              {page === id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="private-card">
            <ShieldCheck size={18} />
            <div>
              Size ait. Cihazınızda.<p>Yerel işleme · Telemetri kapalı</p>
            </div>
          </div>
          <div className="device-label">
            <i className={system ? "online" : ""} />
            <span>
              {gpu?.name?.replace("NVIDIA GeForce ", "") ||
                "Yerel çalışma alanı"}
            </span>
            <span>v1.0</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Çalışma alanı <ChevronRight size={14} />
            <strong>{pages.find((p) => p[0] === page)?.[1]}</strong>
          </div>
          <div className="inline">
            <Tag good={!!system}>
              {system ? "Backend bağlı" : "Backend bekleniyor"}
            </Tag>
            <IconButton label="Durumu yenile" onClick={() => void refresh()}>
              <RefreshCw size={16} />
            </IconButton>
            <button
              className="avatar"
              onClick={() => navigate("settings")}
              aria-label="Ayarları aç"
            >
              AS
            </button>
          </div>
        </header>
        <div className="page">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                ASYA <span>/</span>{" "}
                {page === "studio"
                  ? "METİNDEN SESE"
                  : pages
                      .find((p) => p[0] === page)?.[1]
                      .toLocaleUpperCase("tr-TR")}
              </div>
              <h1>{titleMap[page][0]}</h1>
              <p>{titleMap[page][1]}</p>
            </div>
            {page === "studio" && (
              <Tag good>
                <ShieldCheck size={13} />
                Yerel üretim
              </Tag>
            )}
          </div>
          {error && (
            <div role="alert" className="alert">
              <CircleHelp size={18} />
              <span>{error}</span>
              <IconButton label="Hatayı kapat" onClick={() => setError("")}>
                <X size={16} />
              </IconButton>
            </div>
          )}
          {notice && (
            <div role="status" className="notice">
              <Check size={16} />
              {notice}
            </div>
          )}
          {page === "studio" && (
            <Studio
              voices={voices}
              refresh={refresh}
              settings={settings}
              reuse={reuse}
              fail={fail}
              notify={notify}
            />
          )}
          {page === "dashboard" && (
            <Dashboard
              system={system}
              gpu={gpu}
              navigate={navigate}
              fail={fail}
            />
          )}
          {page === "library" && (
            <Library
              voices={voices}
              settings={settings}
              refresh={refresh}
              fail={fail}
              notify={notify}
            />
          )}
          {page === "history" && (
            <History voices={voices} fail={fail} rerun={rerun} />
          )}
          {page === "chat" && (
            <VoiceChat
              voices={voices}
              settings={settings}
              network={system?.network}
              fail={fail}
            />
          )}
          {page === "settings" && settings && (
            <SettingsPage
              initial={settings}
              voices={voices}
              lm={system?.lm}
              network={system?.network}
              refresh={refresh}
              fail={fail}
              notify={notify}
            />
          )}
          {page === "diagnostics" && (
            <DiagnosticsPage
              gpu={gpu}
              debug={settings?.debug || false}
              fail={fail}
              notify={notify}
            />
          )}
          {!settings && page === "settings" && (
            <Empty
              title="Ayarlar yüklenemedi"
              description="Backend’i başlatın ve durumu yenileyin."
            />
          )}
          <footer>
            <span>
              <ShieldCheck size={13} />
              Sesleriniz bu cihazda işlenir ve saklanır.
            </span>
            <span>
              Chatterbox Multilingual V3 <i /> React + FastAPI
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
