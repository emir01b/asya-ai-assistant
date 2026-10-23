from __future__ import annotations

import asyncio
import copy
import gc
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

import numpy as np
import soundfile as sf

from .core import ROOT, now, uid
from .llm import split_sentences, speech_text
from .providers import ProviderRegistry, ProviderRegistration
from .audio import pace_audio


class TTSProvider(Protocol):
    def load(self, settings: dict): ...
    def generate(self, text: str, language: str, reference: str | None, exaggeration: float, cfg_weight: float): ...
    def unload(self): ...


class ChatterboxProvider:
    name = 'chatterbox'

    def __init__(self):
        self.model = None
        self.device = None
        self.load_seconds = None
        self.default_conditions = None
        self.reference_key = None

    def load(self, settings):
        if self.model is not None:
            return
        os.environ['HF_HUB_OFFLINE'] = '1' if settings['offline'] else '0'
        # from_local makes offline behavior explicit even if HF was previously imported.
        from huggingface_hub import snapshot_download
        from huggingface_hub import constants as hf_constants
        hf_constants.HF_HUB_OFFLINE = settings['offline']
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        import torch
        self.device = settings['tts_device']
        if self.device == 'cuda' and not torch.cuda.is_available():
            raise ValueError('CUDA kullanılamıyor. Ayarlar’dan CPU seçebilirsiniz.')
        start = time.perf_counter()
        snapshot = snapshot_download('ResembleAI/chatterbox', local_files_only=settings['offline'],
                                     allow_patterns=['ve.pt','t3_mtl23ls_v3.safetensors','s3gen.pt',
                                                     'grapheme_mtl_merged_expanded_v1.json','conds.pt','Cangjie5_TC.json'])
        self.model = ChatterboxMultilingualTTS.from_local(Path(snapshot), self.device, t3_model='v3')
        self.default_conditions = copy.deepcopy(self.model.conds)
        self.load_seconds = time.perf_counter() - start

    def generate(self, text, language, reference, exaggeration, cfg_weight):
        import torch
        if self.device == 'cuda':
            torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        if reference is None:
            self.model.conds = copy.deepcopy(self.default_conditions)
            self.reference_key = None
        else:
            path = Path(reference)
            stat = path.stat()
            reference_key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
            if reference_key != self.reference_key:
                # Reuse the active speaker conditioning across streaming chunks.
                # generate() updates emotion conditioning when exaggeration changes.
                self.model.prepare_conditionals(reference, exaggeration=exaggeration)
                self.reference_key = reference_key
        wav = self.model.generate(text, language_id=language, audio_prompt_path=None,
                                  exaggeration=exaggeration, cfg_weight=cfg_weight)
        if self.device == 'cuda':
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        peak = torch.cuda.max_memory_allocated() / 1048576 if self.device == 'cuda' else None
        return wav.squeeze().cpu().numpy(), self.model.sr, elapsed, peak

    def unload(self):
        self.model = None
        self.default_conditions = None
        self.reference_key = None
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def gpu_status():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
        name, total, used, free, utilization = result.stdout.strip().splitlines()[0].split(', ')
        return dict(available=True, name=name, total_mb=int(total), used_mb=int(used),
                    free_mb=int(free), utilization=int(utilization))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return dict(available=False, error=str(exc))


REGISTRY = ProviderRegistry()
REGISTRY.register(ProviderRegistration('chatterbox', 'Chatterbox Multilingual V3', ChatterboxProvider))
REGISTRY.register(ProviderRegistration('fish-s2', 'Fish Audio S2 Pro', None,
    reason='16 GB VRAM üzerinde doğrulanmadı; ayrı adaptör gerektirir.'))


class Engines:
    def __init__(self, store, provider=None):
        self.store = store
        self.provider = provider or REGISTRY.create('chatterbox')
        self.provider_id = 'chatterbox'
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='inference')
        self.gpu_lock = asyncio.Lock()
        self.queue = asyncio.Queue(maxsize=16)
        self.active = None
        self.last_seconds = None
        self.worker = None
        self.stopping = False
        self.stt_state = dict(loaded=False, device=None, error=None)
        self.stt_process = None
        self.stt_log = None
        self.submitted = {}

    async def blocking(self, fn, *args):
        return await asyncio.get_running_loop().run_in_executor(self.executor, fn, *args)

    def start(self):
        self.worker = asyncio.create_task(self.run())

    async def close(self):
        self.stopping = True
        if self.active and self.active != 'stt':
            self.cancel(self.active)
        while not self.queue.empty():
            key = self.queue.get_nowait()
            self.cancel(key)
            self.queue.task_done()
        if self.worker:
            await self.queue.put(None)
            await self.worker
        self.executor.shutdown(wait=True)
        await self.unload_stt()

    async def unload_stt(self, force=False):
        if self.stt_process and self.stt_process.poll() is None and not force:
            self.stt_process.stdin.close()
            try:
                await asyncio.to_thread(self.stt_process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                force = True
        if self.stt_process and self.stt_process.poll() is None:
            if os.name == 'nt':
                # Windows venv python.exe is a redirector. Kill its owned child
                # tree too, otherwise the actual worker retains CUDA and pipes.
                result = await asyncio.to_thread(subprocess.run,
                    ['taskkill', '/PID', str(self.stt_process.pid), '/T', '/F'],
                    capture_output=True, timeout=15,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if result.returncode and self.stt_process.poll() is None:
                    raise ValueError('STT worker process ağacı kapatılamadı: '+result.stderr.decode(errors='replace'))
            else:
                self.stt_process.kill()
            await asyncio.to_thread(self.stt_process.wait)
        if self.stt_process:
            self.stt_process.stdin.close()
            self.stt_process.stdout.close()
        self.stt_process = None
        if self.stt_log:
            self.stt_log.close()
            self.stt_log = None
        self.stt_state['loaded'] = False

    def stt_exchange(self, params):
        # Pipe IO stays off the ASGI loop. Popen also works with the Windows
        # SelectorEventLoop used by uvicorn --reload (async subprocess does not).
        self.stt_process.stdin.write((json.dumps(params)+'\n').encode('utf-8'))
        self.stt_process.stdin.flush()
        return self.stt_process.stdout.readline()

    def submit(self, request):
        if self.stopping or self.queue.full():
            raise ValueError('Üretim kuyruğu dolu. Biraz sonra tekrar deneyin.')
        values = request.model_dump() if hasattr(request, 'model_dump') else dict(request)
        registration = REGISTRY.entries.get(values.get('provider', 'chatterbox'))
        if not registration or not registration.factory:
            raise ValueError('Bu TTS provider kurulu ve doğrulanmış değil.')
        if values.pop('normalize', False):
            values['text'] = speech_text(values['text'])
            if not values['text'].strip():
                raise ValueError('Seslendirilecek konuşma metni bulunamadı.')
        voice_id = values.get('voice_id') or self.store.settings()['default_voice']
        reference = None
        if voice_id:
            voice = self.store.get('voice', voice_id)
            if not voice or not voice['consent']:
                raise ValueError('Ses profili bulunamadı veya kullanım izni yok.')
            reference = str(self.store.asset(voice['asset_id']))
        values.update(voice_id=voice_id or None, reference=reference)
        job = self.store.put('job', {**values, 'status':'queued','progress':0,'segments':[],
                                   'error':None,'metrics':{},'asset_id':None})
        self.queue.put_nowait(job['id'])
        self.submitted[job['id']] = time.perf_counter()
        return job

    def cancel(self, key):
        job = self.store.get('job', key)
        if not job:
            raise ValueError('İş bulunamadı.')
        if job['status'] in ('queued', 'running'):
            job['status'] = 'cancelling' if self.active == key else 'cancelled'
            self.store.put('job', job)
        return job

    def update(self, key, **values):
        with self.store.lock:
            job = self.store.get('job', key)
            job.update(values)
            return self.store.put('job', job)

    async def run(self):
        while True:
            key = await self.queue.get()
            try:
                if key is None:
                    return
                job = self.store.get('job', key)
                if job['status'] == 'cancelled':
                    continue
                async with self.gpu_lock:
                    self.active = key
                    # A queued job might have been cancelled while waiting for STT.
                    if self.store.get('job', key)['status'] == 'cancelled':
                        continue
                    await self.generate(key)
            except Exception as exc:
                message = str(exc)
                if 'out of memory' in message.lower():
                    message = 'GPU belleği yetersiz. LM Studio modelini küçültün veya TTS modelini boşaltın. ' + message
                    await self.blocking(self.provider.unload)
                if key:
                    self.update(key, status='failed', error=message)
                    self.store.error('tts', message)
            finally:
                if key:
                    self.submitted.pop(key, None)
                self.active = None
                self.queue.task_done()

    async def generate(self, key):
        work_started = time.perf_counter()
        started = self.submitted.pop(key, work_started)
        queue_seconds = work_started - started
        self.update(key, status='running')
        job = self.store.get('job', key)
        if job['provider'] != self.provider_id:
            await self.blocking(self.provider.unload)
            self.provider = REGISTRY.create(job['provider'])
            self.provider_id = job['provider']
        await self.blocking(self.provider.load, self.store.settings())
        job = self.store.get('job', key)
        parts = split_sentences(job['text'], min_chars=job.get('min_segment_chars',0))
        chunks, segments, peak_mb = [], [], None
        synthesis = 0
        for index, part in enumerate(parts):
            if self.store.get('job', key)['status'] == 'cancelling':
                self.update(key, status='cancelled')
                return
            samples, sr, elapsed, peak = await self.blocking(self.provider.generate, part,
                job['language'], job['reference'], job['exaggeration'], job['cfg_weight'])
            if job.get('speech_rate', 1.0) != 1.0 or job.get('trailing_pause_ms', 0):
                samples = await asyncio.to_thread(pace_audio, samples, sr,
                    job.get('speech_rate', 1.0), job.get('trailing_pause_ms', 0))
            if self.store.get('job', key)['status'] == 'cancelling':
                self.update(key, status='cancelled')
                return
            path = self.store.root / 'generations' / f'{key}-{index}.wav'
            await asyncio.to_thread(sf.write, str(path), samples, sr, subtype='PCM_16')
            asset = self.store.add_asset(path, duration=len(samples)/sr, sample_rate=sr)
            segment = dict(index=index, text=part, asset_id=asset['id'], duration=len(samples)/sr,
                           generation_seconds=elapsed, ready_seconds=time.perf_counter()-started)
            segments.append(segment)
            chunks.extend([samples, np.zeros(0 if job.get('trailing_pause_ms') else int(sr * .16), dtype=np.float32)])
            synthesis += elapsed
            peak_mb = max(peak_mb or 0, peak or 0) or None
            self.update(key, progress=(index+1)/len(parts), segments=list(segments))
        path = self.store.root / 'generations' / f'{key}.wav'
        audio = np.concatenate(chunks[:-1])
        await asyncio.to_thread(sf.write, str(path), audio, sr, subtype='PCM_16')
        duration = len(audio)/sr
        asset = self.store.add_asset(path, duration=duration, sample_rate=sr)
        total = time.perf_counter()-started
        self.last_seconds = total
        metrics = dict(total_seconds=total, synthesis_seconds=synthesis, duration=duration,
                       first_audio_seconds=segments[0]['ready_seconds'], rtf=synthesis/duration,
                       peak_vram_mb=peak_mb, model_load_seconds=self.provider.load_seconds,
                       queue_seconds=queue_seconds)
        self.update(key, status='completed', progress=1, asset_id=asset['id'], metrics=metrics)
        self.store.put('benchmark', dict(source='tts', job_id=key, **metrics))

    async def wait_job(self, key):
        while True:
            job = self.store.get('job', key)
            if job['status'] in ('completed','cancelled','failed'):
                return job
            await asyncio.sleep(.05)

    async def transcribe(self, path: Path, language: str | None):
        settings = self.store.settings()
        python = ROOT / '.venv-stt' / 'Scripts' / 'python.exe'
        if not python.is_file():
            raise ValueError('STT ortamı kurulu değil. scripts/setup-stt.ps1 çalıştırın.')
        if self.gpu_lock.locked():
            self.stt_state['waiting'] = True
        async with self.gpu_lock:
            self.active = 'stt'
            self.stt_state['waiting'] = False
            try:
                if not self.stt_process or self.stt_process.poll() is not None:
                    await self.unload_stt()
                    self.stt_log = (self.store.root/'stt-worker.log').open('ab')
                    self.stt_process = subprocess.Popen([str(python), '-u',
                        str(ROOT/'apps/backend/stt_worker.py'), '--serve'], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=self.stt_log,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                params = dict(path=str(path), model_name=settings['stt_model'], device=settings['stt_device'],
                              language=language or 'auto', offline='1' if settings['offline'] else '0',
                              fallback='1' if settings['stt_cpu_fallback'] else '0')
                try:
                    stdout = await asyncio.wait_for(asyncio.to_thread(self.stt_exchange, params), timeout=300)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    await self.unload_stt(force=True)
                    raise
                if not stdout:
                    await self.unload_stt()
                    details = (self.store.root/'stt-worker.log').read_text(errors='replace')[-1500:]
                    raise ValueError('STT worker durdu: ' + details)
                result = json.loads(stdout.decode('utf-8'))
                if result.get('error'):
                    raise ValueError(result['error'])
                self.stt_state.update(loaded=True, device=result['device'], error=None,
                                      last_seconds=result['seconds'], warning=result.get('warning'))
                self.store.put('benchmark', dict(source='stt', **result))
                return result
            except Exception as exc:
                message = str(exc) or type(exc).__name__
                self.stt_state['error'] = message
                self.store.error('stt', message)
                raise ValueError(message) from exc
            finally:
                self.active = None

    def status(self):
        return dict(provider=self.provider_id, loaded=self.provider.model is not None,
                    device=self.provider.device, model_load_seconds=self.provider.load_seconds,
                    active=self.active, pending=self.queue.qsize(), last_seconds=self.last_seconds)
