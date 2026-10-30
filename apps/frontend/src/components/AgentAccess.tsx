import { useEffect, useState } from 'react';
import { api } from '../api';

type Agent = { id: string; name: string; revoked: boolean };
type State = { enabled: boolean; agents: Agent[]; url: string; guide: string; scopes: string[] };
type Installation = { status: string; installed: boolean; progress: number; message: string; error: string | null; running: boolean };

export default function AgentAccess() {
  const [state, setState] = useState<State>();
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [installation, setInstallation] = useState<Installation>();
  const [scopes, setScopes] = useState(['status:read', 'voices:read', 'speech:write', 'jobs:own']);
  const refresh = async () => setState(await api<State>('/agent-admin'));
  useEffect(() => { void refresh().catch(e => setError(String(e))); }, []);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await api<Installation>('/agent-admin/installation');
        if (active) setInstallation(result);
      } catch (e) { if (active) setError(String(e)); }
      if (active) timer = setTimeout(() => void poll(), 1500);
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, []);
  async function act(action: () => Promise<unknown>) {
    setBusy(true); setError('');
    try { await action(); await refresh(); } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }
  return <section className="panel padded">
    <h2>Ajan erişimi</h2>
    <p>OpenClaw ve diğer ajanlar arayüzü kullanmadan API veya MCP ile ses üretebilir.</p>
    <div className="toolbar">
    <label className="checkbox">
      <input type="checkbox" role="switch" checked={state?.enabled ?? false} disabled={!state || busy || (!state.enabled && (!installation?.installed || installation.status === 'installing'))}
        onChange={e => { const enabled = e.target.checked; void act(() => api('/agent-admin/access', { method: 'PUT', body: JSON.stringify({ enabled }) })); }} />
      Ajan erişimine izin ver
    </label>
    <button className="button secondary" disabled={busy || !installation || installation.installed || installation.status === 'installing'}
      onClick={() => void act(async () => setInstallation(await api<Installation>('/agent-admin/installation', { method: 'POST' })))}>
      {!installation ? 'Kontrol ediliyor…' : installation.status === 'installing' ? 'Kuruluyor…' : installation.installed ? 'Zaten kurulu' : installation.status === 'error' ? 'Tekrar dene' : 'Kur'}
    </button>
    </div>
    <div aria-live="polite">
      <p className="help-text">{installation?.message || 'Kurulum durumu kontrol ediliyor.'}</p>
      {installation?.status === 'installing' && <>
        <progress aria-label="Ajan servisi kurulum ilerlemesi" max={100} value={installation.progress} style={{ width: '100%' }} />
        <p className="help-text">Kurulum aşamaları: %{installation.progress}. Bu oran indirilen dosya miktarını göstermez.</p>
      </>}
      {installation?.error && <p className="error-text">{installation.error}</p>}
    </div>
    {!installation?.installed && <p className="help-text">İlk kurulum internet bağlantısı gerektirir. Ses modelleriniz yeniden indirilmez.</p>}
    <p className="help-text">Değişiklik hemen kaydedilir. Kapalıyken yalnızca bilgi adresi yanıt verir; tüm API ve MCP işlemleri engellenir. Başlamış bir ses üretimi arka planda tamamlanabilir, ajan sonucu indiremez.</p>
    {state && <>
      <p className="help-text">Bağlantı: {state.url} · MCP: {state.url}/mcp</p>
      <p className="help-text">Bilgi adresi: {state.guide}. Kurulum tamamlandığında ajan servisi otomatik başlatılır.</p>
      <label htmlFor="agent-name">AJAN ADI</label>
      <input id="agent-name" value={name} maxLength={80} onChange={e => setName(e.target.value)} />
      <button className="button secondary" disabled={busy || !name.trim()} onClick={() => void act(async () => {
        const created = await api<{ token: string }>('/agent-admin/keys', { method: 'POST', body: JSON.stringify({ name, scopes }) });
        setToken(created.token); setName('');
      })}>Erişim anahtarı oluştur</button>
      <p className="help-text">Varsayılan izinler: durum, ses profillerini listeleme, ses üretme ve yalnızca kendi işlerine erişme.</p>
      <details><summary>Ek izinler (isteğe bağlı)</summary>
        {state.scopes.filter(s => !['status:read', 'voices:read', 'speech:write', 'jobs:own'].includes(s)).map(scope =>
          <label className="checkbox" key={scope}><input type="checkbox" checked={scopes.includes(scope)}
            onChange={e => setScopes(previous => e.target.checked ? [...previous, scope] : previous.filter(s => s !== scope))} />
            {({ 'transcription:write': 'Sesi yazıya çevirme', 'voices:write': 'Ses profili oluşturma ve düzenleme', 'voices:delete': 'Paylaşılan ses profillerini silme', 'settings:read': 'Ses ayarlarını okuma', 'settings:write': 'Ses ayarlarını değiştirme', 'models:unload': 'Modelleri bellekten çıkarma', 'history:delete': 'Kendi üretim geçmişini silme' } as Record<string, string>)[scope] || scope}
          </label>)}
      </details>
      {token && <><label htmlFor="agent-token">ANAHTAR (YALNIZCA BİR KEZ GÖSTERİLİR)</label>
        <input id="agent-token" readOnly value={token} />
        <button className="button secondary" onClick={() => setToken('')}>Anahtarı gizle</button></>}
      {state.agents.map(agent => <div className="toolbar" key={agent.id}>
        <span>{agent.name} · {agent.revoked ? 'İptal edilmiş' : 'Etkin anahtar'}</span>
        {!agent.revoked && <button className="button secondary" disabled={busy} onClick={() => void act(() => api(`/agent-admin/keys/${agent.id}`, { method: 'DELETE' }))}>Anahtarı iptal et</button>}
      </div>)}
    </>}
    {error && <p className="error-text">{error}</p>}
  </section>;
}
