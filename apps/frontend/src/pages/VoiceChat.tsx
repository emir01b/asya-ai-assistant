import { useState, useEffect, useRef, useCallback } from "react";
import {
  MessageCircle,
  Mic,
  MicOff,
  AudioLines,
  Plus,
  Trash2,
  Send,
  Volume2,
  RefreshCw,
} from "lucide-react";
import { api, audioUrl, statusLabel, generateAudio } from "../api";
import { IconButton, Tag, VoiceSelect, type Feedback } from "../components/ui";
import type {
  Conversation,
  Message,
  Settings,
  Voice,
  Job,
  SystemStatus,
  LMStatus,
} from "../types";
import { AudioQueue, Microphone } from "../audio";
import { requestId } from "../request-id";
import LanHttpsSetup from "../components/LanHttpsSetup";

export default function VoiceChat({
  voices,
  settings,
  network,
  fail,
}: {
  voices: Voice[];
  settings: Settings | null;
  network: SystemStatus["network"];
  fail: Feedback["fail"];
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [cid, setCid] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [voice, setVoice] = useState(settings?.default_voice || "");
  const [model, setModel] = useState(settings?.llm_model || "");
  const modelRef = useRef(model);
  const modelChanged = useRef(false);
  const [models, setModels] = useState<LMStatus["models"]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState("");
  const modelsRequest = useRef(0);
  const modelsAbort = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!modelChanged.current) {
      modelRef.current = settings?.llm_model || "";
      setModel(modelRef.current);
    }
  }, [settings?.llm_model]);
  const loadModels = useCallback(async () => {
    const generation = ++modelsRequest.current;
    modelsAbort.current?.abort();
    const controller = new AbortController();
    modelsAbort.current = controller;
    setModelsLoading(true);
    setModelsError("");
    try {
      const result = await api<LMStatus>("/llm/models", {
        signal: controller.signal,
      });
      if (generation !== modelsRequest.current) return;
      if (!result.connected)
        throw new Error(result.error || "LM Studio bağlantısı kurulamadı.");
      setModels(result.models);
    } catch (error) {
      if (generation !== modelsRequest.current || controller.signal.aborted)
        return;
      setModelsError(
        error instanceof Error ? error.message : "Modeller alınamadı.",
      );
    } finally {
      if (generation === modelsRequest.current) setModelsLoading(false);
    }
  }, []);
  useEffect(() => {
    void loadModels();
    return () => {
      modelsRequest.current++;
      modelsAbort.current?.abort();
    };
  }, [loadModels]);
  const [state, setState] = useState("idle");
  const [connected, setConnected] = useState(false);
  const [listening, setListening] = useState(false);
  const [level, setLevel] = useState(0);
  const [speak, setSpeak] = useState(true);
  const [audioAssets, setAudioAssets] = useState<string[]>([]);
  const [bargeIn, setBargeIn] = useState(false);
  const [micStarting, setMicStarting] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const request = useRef("");
  const session = useRef<string | null>(null);
  const queue = useRef(new AudioQueue());
  const microphone = useRef<Microphone | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  const listeningRef = useRef(false);
  const voiceRef = useRef(voice);
  const speakRef = useRef(speak);
  const revoiceJobs = useRef(new Set<string>());
  const bargeInRef = useRef(false);
  const inputEpoch = useRef(0);
  const uploadAbort = useRef<AbortController | null>(null);
  const syncMicrophone = useCallback(() => {
    microphone.current?.setSuspended(
      !bargeInRef.current && (busy.current || queue.current.current !== null),
    );
  }, []);
  useEffect(() => {
    bargeInRef.current = bargeIn;
    syncMicrophone();
  }, [bargeIn, syncMicrophone]);
  useEffect(() => {
    voiceRef.current = voice;
    speakRef.current = speak;
  }, [voice, speak]);
  const loadConversations = useCallback(
    () =>
      api<Conversation[]>("/conversations").then(setConversations).catch(fail),
    [fail],
  );
  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);
  useEffect(() => {
    session.current = cid;
  }, [cid]);
  useEffect(() => {
    queue.current.output = settings?.output_id || "";
  }, [settings?.output_id]);
  useEffect(() => {
    queue.current.onError = (message) => fail(new Error(message));
    queue.current.onState = (playing) => {
      syncMicrophone();
      if (playing) setState("speaking");
      else if (!busy.current)
        setState(listeningRef.current ? "listening" : "idle");
    };
  }, [fail, syncMicrophone]);
  useEffect(() => {
    const socket = new WebSocket(
      `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/v1/realtime/voice`,
    );
    ws.current = socket;
    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      busy.current = false;
      queue.current.stop();
      setState("error");
    };
    socket.onerror = () =>
      fail(
        new Error(
          "Sesli sohbet bağlantısı kurulamadı. Backend durumunu kontrol edin.",
        ),
      );
    socket.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.request_id && event.request_id !== request.current) return;
      if (event.type === "start") {
        session.current = event.conversation_id;
        setCid(event.conversation_id);
        setMessages((v) => [
          ...v.filter((m) => m.id !== "pending-user"),
          event.user,
        ]);
      }
      if (event.type === "token")
        setMessages((v) => {
          const old = v.find((m) => m.id === event.message_id);
          return old
            ? v.map((m) =>
                m.id === event.message_id
                  ? { ...m, content: m.content + event.token }
                  : m,
              )
            : [
                ...v,
                {
                  id: event.message_id,
                  role: "assistant",
                  content: event.token,
                  created_at: new Date().toISOString(),
                },
              ];
        });
      if (event.type === "state" && !queue.current.current)
        setState(event.state);
      if (event.type === "audio") {
        setAudioAssets((v) => [...v, event.asset_id]);
        queue.current.push(event.asset_id);
      }
      if (event.type === "transcript" && event.warning)
        fail(new Error(event.warning));
      if (event.type === "done") {
        busy.current = false;
        syncMicrophone();
        setMessages((v) =>
          v.map((m) => (m.id === event.message.id ? event.message : m)),
        );
        if (!queue.current.current)
          setState(listeningRef.current ? "listening" : "idle");
        void loadConversations();
      }
      if (event.type === "error") {
        busy.current = false;
        queue.current.stop();
        setState("error");
        fail(new Error(event.message));
      }
      if (event.type === "ignored") {
        busy.current = false;
        syncMicrophone();
        if (!queue.current.current)
          setState(listeningRef.current ? "listening" : "idle");
      }
    };
    return () => {
      inputEpoch.current++;
      uploadAbort.current?.abort();
      request.current = requestId();
      for (const id of revoiceJobs.current)
        void api(`/tts/jobs/${id}/cancel`, { method: "POST" }).catch(fail);
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
      queue.current.stop();
      microphone.current?.stop(false);
    };
  }, [fail, loadConversations, syncMicrophone]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);
  function interrupt() {
    inputEpoch.current++;
    uploadAbort.current?.abort();
    const previous = request.current;
    request.current = requestId();
    queue.current.stop();
    setAudioAssets([]);
    for (const id of revoiceJobs.current)
      void api(`/tts/jobs/${id}/cancel`, { method: "POST" }).catch(fail);
    revoiceJobs.current.clear();
    busy.current = false;
    syncMicrophone();
    if (ws.current?.readyState === WebSocket.OPEN)
      ws.current.send(
        JSON.stringify({ type: "interrupt", request_id: previous }),
      );
    setState("interrupted");
  }
  async function revoice(message: Message) {
    interrupt();
    const generation = request.current;
    busy.current = true;
    syncMicrophone();
    setState("synthesizing");
    let key: string | null = null;
    try {
      const job = await generateAudio({
        text: message.content,
        normalize: true,
        voice_id: voice || null,
        language: settings?.language || "tr",
      });
      key = job.id;
      revoiceJobs.current.add(key);
      let result = job;
      while (["queued", "running", "cancelling"].includes(result.status)) {
        if (generation !== request.current) {
          await api(`/tts/jobs/${key}/cancel`, { method: "POST" });
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 600));
        result = await api<Job>(`/tts/jobs/${key}`);
      }
      if (generation !== request.current) return;
      if (!result.asset_id) throw new Error(result.error || "Ses üretilemedi.");
      setAudioAssets([result.asset_id]);
      queue.current.push(result.asset_id);
    } catch (error) {
      if (generation === request.current) fail(error);
    } finally {
      if (key) revoiceJobs.current.delete(key);
      if (generation === request.current) {
        busy.current = false;
        syncMicrophone();
      }
    }
  }
  function send(content: string, type = "message", asset_id?: string) {
    if (!connected || ws.current?.readyState !== WebSocket.OPEN) {
      fail(
        new Error("WebSocket bağlantısı hazır değil. Sayfayı yeniden açın."),
      );
      return;
    }
    queue.current.stop();
    inputEpoch.current++;
    setAudioAssets([]);
    request.current = requestId();
    busy.current = true;
    syncMicrophone();
    setState(type === "audio" ? "transcribing" : "thinking");
    if (type === "message")
      setMessages((v) => [
        ...v,
        {
          id: "pending-user",
          role: "user",
          content,
          created_at: new Date().toISOString(),
        },
      ]);
    ws.current?.send(
      JSON.stringify({
        type,
        text: content,
        asset_id,
        request_id: request.current,
        conversation_id: session.current,
        voice_id: voiceRef.current || null,
        speak: speakRef.current,
        model: modelRef.current || null,
      }),
    );
    setText("");
  }
  async function toggleMic() {
    if (listening) {
      microphone.current?.stop(false);
      setListening(false);
      listeningRef.current = false;
      if (!busy.current && !queue.current.current) setState("idle");
      return;
    }
    if (micStarting) return;
    if (!window.isSecureContext) {
      fail(
        new Error(
          "Yerel ağda mikrofon kullanmak için HTTPS gerekir. Sunucu bilgisayarında http://localhost:8000 kullanabilirsiniz. Yazılı sohbet ve ses oynatma HTTP üzerinden çalışır.",
        ),
      );
      return;
    }
    if (!navigator.mediaDevices || !window.AudioWorkletNode) {
      fail(
        new Error(
          "Tarayıcı mikrofon kaydını desteklemiyor. localhost üzerinde güncel bir tarayıcı kullanın.",
        ),
      );
      return;
    }
    const mic = new Microphone();
    mic.threshold = settings?.vad_threshold || 0.018;
    mic.silenceMs = settings?.vad_silence_ms || 1000;
    mic.onLevel = setLevel;
    mic.onSpeech = () => {
      inputEpoch.current++;
      if (bargeInRef.current && (busy.current || queue.current.current))
        interrupt();
      setState("speech_detected");
    };
    mic.onRecording = (blob) => {
      const epoch = ++inputEpoch.current;
      busy.current = true;
      syncMicrophone();
      setState("transcribing");
      uploadAbort.current?.abort();
      const controller = new AbortController();
      uploadAbort.current = controller;
      const form = new FormData();
      form.append("file", blob, "microphone.wav");
      void api<{ id: string }>("/audio/recordings", {
        method: "POST",
        body: form,
        signal: controller.signal,
      })
        .then((asset) => {
          if (epoch === inputEpoch.current) send("", "audio", asset.id);
        })
        .catch((e) => {
          if (epoch !== inputEpoch.current || controller.signal.aborted) return;
          busy.current = false;
          syncMicrophone();
          setState("error");
          fail(e);
        });
    };
    microphone.current = mic;
    setMicStarting(true);
    try {
      await mic.start(settings?.microphone_id || "");
      if (microphone.current !== mic || !mic.active) return;
      setListening(true);
      listeningRef.current = true;
      syncMicrophone();
      if (!busy.current && !queue.current.current) setState("listening");
    } catch (e) {
      mic.stop(false);
      fail(
        new Error(`Mikrofon açılamadı: ${e instanceof Error ? e.message : e}`),
      );
    } finally {
      setMicStarting(false);
    }
  }
  async function selectConversation(id: string | null) {
    interrupt();
    session.current = id;
    setCid(id);
    setMessages([]);
    setAudioAssets([]);
    if (id)
      try {
        const c = await api<Conversation>(`/conversations/${id}`);
        setMessages(c.messages || []);
      } catch (e) {
        fail(e);
      }
  }
  return (
    <>
      <LanHttpsSetup network={network} />
      <div className="chat-layout">
        <aside className="panel conversation-sidebar">
          <button
            className="button secondary"
            onClick={() => void selectConversation(null)}
          >
            <Plus size={16} />
            Yeni konuşma
          </button>
          <div className="conversation-list">
            {conversations.map((c) => (
              <div key={c.id} className={c.id === cid ? "selected" : ""}>
                <button onClick={() => void selectConversation(c.id)}>
                  <MessageCircle size={15} />
                  <span>{c.title}</span>
                </button>
                <IconButton
                  label="Konuşmayı sil"
                  onClick={() =>
                    void api(`/conversations/${c.id}`, { method: "DELETE" })
                      .then(() => {
                        if (cid === c.id) void selectConversation(null);
                        return loadConversations();
                      })
                      .catch(fail)
                  }
                >
                  <Trash2 size={13} />
                </IconButton>
              </div>
            ))}
          </div>
        </aside>
        <section className="panel chat-panel">
          <div className="chat-top">
            <Tag good={connected}>
              {connected ? "Sohbet bağlı" : "Bağlı değil"}
            </Tag>
            <div className="chat-model-picker">
              <div className="chat-model-controls">
                <select
                  aria-label="Sohbet modeli"
                  value={model}
                  onChange={(e) => {
                    modelChanged.current = true;
                    modelRef.current = e.target.value;
                    setModel(e.target.value);
                  }}
                >
                  <option value="">Model seçin</option>
                  {model && !models.some((item) => item.id === model) && (
                    <option value={model}>{model} (listede yok)</option>
                  )}
                  {models.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.id}
                    </option>
                  ))}
                </select>
                <IconButton
                  label="Modelleri yenile"
                  onClick={() => void loadModels()}
                >
                  <RefreshCw size={14} />
                </IconButton>
              </div>
              <span
                className="muted chat-model-status"
                role="status"
                aria-live="polite"
              >
                {modelsLoading
                  ? "Modeller yükleniyor…"
                  : modelsError
                    ? `Modeller alınamadı: ${modelsError}`
                    : !models.length
                      ? "LM Studio model listesi boş. Bir model yükleyip yenileyin."
                      : "Seçiminiz sonraki mesajda kullanılır."}
              </span>
            </div>
            <VoiceSelect voices={voices} value={voice} onChange={setVoice} />
            <label className="checkbox">
              <input
                type="checkbox"
                checked={speak}
                onChange={(e) => setSpeak(e.target.checked)}
              />
              Sesli yanıt
            </label>
            <label
              className="checkbox"
              title="Açıkken doğrulanmış konuşmanız AI yanıtını kesebilir. Varsayılan kapalı, yanıtlar tamamlanana kadar mikrofon bekler."
            >
              <input
                type="checkbox"
                checked={bargeIn}
                onChange={(e) => setBargeIn(e.target.checked)}
              />
              Konuşarak araya gir
            </label>
          </div>
          <div className="messages">
            {!messages.length && (
              <div className="chat-empty">
                <div className="chat-orb">
                  <AudioLines size={42} />
                </div>
                <h2>Merhaba, sizi dinliyorum.</h2>
                <p>
                  Bir mesaj yazın veya mikrofonu açın.
                  <br />
                  Konuşmanız bittiğinde yanıt otomatik hazırlanır.
                </p>
                <span className="muted">
                  {model
                    ? `Sohbet modeli: ${model}. Yukarıdaki seçiciden değiştirebilirsiniz.`
                    : "Yukarıdaki Sohbet modeli seçicisinden bir LM Studio modeli seçin."}
                </span>
              </div>
            )}
            {messages.map((m) => (
              <article className={`message ${m.role}`} key={m.id}>
                <span className="message-avatar">
                  {m.role === "user" ? "SİZ" : <AudioLines size={17} />}
                </span>
                <div>
                  <div className="message-label">
                    {m.role === "user" ? "Siz" : "Voice Assistant"}
                    {m.interrupted && <span> · Kesildi</span>}
                  </div>
                  <p>{m.content}</p>
                  {m.role === "assistant" && (
                    <button
                      className="text-link"
                      onClick={() => void revoice(m)}
                    >
                      <Volume2 size={13} />
                      Yeniden seslendir
                    </button>
                  )}
                </div>
              </article>
            ))}
            <div ref={bottom} />
          </div>
          {audioAssets.length > 0 && (
            <div className="chat-audio">
              <audio controls src={audioUrl(audioAssets.at(-1)!)} />
              <span>Son ses segmenti</span>
              <button
                className="text-link"
                onClick={() => void queue.current.resume()}
              >
                Ses kuyruğunu oynat
              </button>
            </div>
          )}
          <div className="chat-status">
            <i className={`state-dot ${busy.current ? "pulse" : ""}`} />
            {statusLabel[state] || state}
            {listening &&
              !bargeIn &&
              (busy.current || queue.current.current) && (
                <span> · Mikrofon yanıt bitince açılacak</span>
              )}
            {listening && (
              <div className="mic-level">
                <i style={{ width: `${Math.min(100, level * 1000)}%` }} />
              </div>
            )}
            {busy.current && (
              <button className="text-link" onClick={interrupt}>
                Yanıtı durdur
              </button>
            )}
          </div>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              if (text.trim()) send(text);
            }}
          >
            <IconButton
              label={listening ? "Mikrofonu kapat" : "Mikrofonu aç"}
              onClick={() => void toggleMic()}
              disabled={!connected || micStarting}
            >
              {listening ? <MicOff size={20} /> : <Mic size={20} />}
            </IconButton>
            <input
              aria-label="Sohbet mesajı"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Bir mesaj yazın…"
              maxLength={12000}
            />
            <button
              className="send-button"
              aria-label="Mesaj gönder"
              disabled={!text.trim() || !connected}
            >
              <Send size={19} />
            </button>
          </form>
          <p className="chat-footnote">
            {bargeIn
              ? "Konuşarak araya girme açık; konuşmanız yanıtı keser."
              : "Yanıtlar tamamlanana kadar mikrofon bekler. Araya girmek için Yanıtı durdur düğmesini kullanabilirsiniz."}
          </p>
        </section>
      </div>
    </>
  );
}
