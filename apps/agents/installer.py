"""Local-only, fixed-command installer for the optional agent environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


class AgentRuntime:
    def __init__(self, root=ROOT, data=None):
        self.root = Path(root)
        self.data = Path(data) if data else self.root / 'data' / 'agents'
        self.python = self.root / '.venv-agents' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        self.requirements = self.root / 'apps/agents/requirements.txt'
        self.lock = threading.RLock()
        self.worker = None
        self.process = None
        self.install_process = None
        self.stopping = threading.Event()
        self.checked = 0.0
        self.state = dict(status='checking', installed=False, progress=0,
                          message='Kurulum kontrol ediliyor.', error=None, running=False)

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def probe(self):
        if not self.python.is_file():
            return False
        # Test imports and the pinned versions; an empty/broken venv is not installed.
        code = """import sys, pathlib, importlib.metadata as m
assert sys.version_info[:2] == (3, 11)
import fastapi, uvicorn, httpx, multipart
from mcp.server import MCPServer
for line in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines():
    if '==' in line and not line.lstrip().startswith('#'):
        name, version = line.strip().split('==', 1)
        assert m.version(name) == version, name
"""
        try:
            result = subprocess.run([str(self.python), '-I', '-c', code, str(self.requirements)],
                cwd=self.root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=30, creationflags=HIDDEN)
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def refresh(self):
        with self.lock:
            if self.state['status'] == 'installing':
                return self.snapshot()
            if self.checked and time.monotonic() - self.checked < 30:
                return self.snapshot()
            installed = self.probe()
            self.checked = time.monotonic()
            if self.state['status'] != 'error' or installed:
                self.state.update(status='installed' if installed else 'not_installed', error=None,
                    message='Ajan servisi kurulu.' if installed else 'Ajan servisi henüz kurulu değil.')
            self.state.update(installed=installed, progress=100 if installed else 0,
                              running=self.is_running())
            return self.snapshot()

    def is_running(self):
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open('http://127.0.0.1:8002/.well-known/asya-agent.json', timeout=2) as response:
                return json.load(response).get('name') == 'ASYA'
        except (OSError, ValueError):
            return False

    def ensure_running(self):
        with self.lock:
            if self.stopping.is_set():
                raise RuntimeError('Uygulama kapanıyor; servisi sonraki açılışta başlatın.')
            if self.is_running():
                self.state['running'] = True
                return
            if not self.state['installed']:
                raise RuntimeError('Önce ajan servisini kurun.')
            self.data.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ, VOICE_DATA_DIR=str(self.data.parent), PYTHONUTF8='1')
            env.pop('ASYA_AGENT_LAN_IP', None)
            # Fixed loopback listener; no commands or paths come from HTTP input.
            with (self.data / 'service.log').open('ab') as log:
                self.process = subprocess.Popen([str(self.python), '-m', 'apps.agents.serve'],
                    cwd=self.root, env=env, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, creationflags=HIDDEN)
            for _ in range(40):
                if self.is_running():
                    self.state['running'] = True
                    return
                if self.process.poll() is not None:
                    break
                time.sleep(.25)
            raise RuntimeError('Kurulum hazır, ancak ajan servisi başlatılamadı. Port 8002 ve data/agents/service.log dosyasını kontrol edin.')

    def run(self, command, log):
        if self.stopping.is_set():
            raise RuntimeError('Uygulama kapatıldığı için kurulum durduruldu. Tekrar deneyebilirsiniz.')
        process = subprocess.Popen(command, cwd=self.root, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=HIDDEN,
            env=dict(os.environ, PIP_DISABLE_PIP_VERSION_CHECK='1', PYTHONUTF8='1'))
        self.install_process = process
        try:
            if self.stopping.is_set():
                process.terminate()
            result = process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError('Kurulum zaman aşımına uğradı. İnternet bağlantısını kontrol edip tekrar deneyin.') from None
        finally:
            self.install_process = None
        if result:
            raise RuntimeError('Kurulum komutu başarısız oldu. İnternet bağlantısını kontrol edip tekrar deneyin. Ayrıntılar: data/agents/install.log')

    def install(self):
        with self.lock:
            if self.state['status'] == 'installing':
                return self.snapshot()
            if self.refresh()['installed']:
                return self.snapshot()
            self.update(status='installing', progress=5, error=None, message='Kurulum hazırlanıyor.')
            self.worker = threading.Thread(target=self._install, daemon=True, name='asya-agent-install')
            self.worker.start()
            return self.snapshot()

    def _install(self):
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            with (self.data / 'install.log').open('ab') as log:
                self.update(progress=10, message='Python 3.11 ortamı hazırlanıyor.')
                if not self.python.exists():
                    base = [sys.executable] if sys.version_info[:2] == (3, 11) else ['py', '-3.11']
                    self.run(base + ['-m', 'venv', str(self.root / '.venv-agents')], log)
                self.update(progress=30, message='Gerekli paketler indiriliyor ve kuruluyor. Bu adım birkaç dakika sürebilir.')
                self.run([str(self.python), '-m', 'pip', 'install', '--no-input', '-r', str(self.requirements)], log)
                self.update(progress=85, message='Kurulum doğrulanıyor.')
                if not self.probe():
                    raise RuntimeError('Kurulum doğrulanamadı. Python 3.11 ve paketleri kontrol edin: data/agents/install.log')
                self.update(installed=True, progress=95, message='Ajan servisi başlatılıyor.')
                self.ensure_running()
                self.update(status='installed', progress=100, message='Kurulum tamamlandı. Ajan erişimini ayrıca açabilirsiniz.')
                self.checked = time.monotonic()
        except Exception as exc:
            self.update(status='error', message='Kurulum tamamlanamadı.', error=str(exc))
            self.checked = time.monotonic()

    def startup(self):
        def work():
            if self.refresh()['installed']:
                try:
                    self.ensure_running()
                except Exception as exc:
                    self.update(error=str(exc))
        threading.Thread(target=work, daemon=True, name='asya-agent-start').start()

    def close(self):
        self.stopping.set()
        process = self.install_process
        if process and process.poll() is None:
            process.terminate()
        if self.worker:
            self.worker.join(timeout=5)
        # Only stop the child owned by this backend, never a separately launched service.
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
