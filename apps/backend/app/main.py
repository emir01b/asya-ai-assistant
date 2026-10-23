from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .core import Store, ROOT, uid
from .schemas import Generation, Settings, Chat, VoiceUpdate, ConversationCreate, LANGUAGES, Job, Voice
from .engines import Engines, gpu_status, REGISTRY
from .llm import LMClient
from .chat import ChatService
from .audio import MAX_UPLOAD, convert_audio, export_mp3, peaks
from .network import NetworkAccess

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger('asya')
def create_app(store=None, provider=None, network=None):
    network = network or NetworkAccess.from_env()
    store = store or Store()
    engines = Engines(store, provider)
    lm = LMClient(store)
    chat = ChatService(store, lm, engines)

    @asynccontextmanager
    async def lifespan(app):
        store.recover_jobs()
        engines.start()
        log.info(json.dumps(dict(event='startup', data_dir=str(store.root))))
        yield
        await engines.close()

    app = FastAPI(title='ASYA', version='1.0.0', lifespan=lifespan)
    app.state.store, app.state.engines, app.state.lm = store, engines, lm
    app.add_middleware(CORSMiddleware, allow_origins=sorted(network.origins),
                       allow_methods=['GET','POST','PUT','DELETE'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def local_access(request: Request, call_next):
        origin = request.headers.get('origin')
        host = request.url.hostname
        if host not in network.hosts:
            return JSONResponse({'detail':'Bu sunucu adresine erişim açık değil.'}, status_code=403)
        if origin and origin not in network.origins:
            return JSONResponse({'detail':'Origin erişimi reddedildi.'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail':'Siteler arası erişim reddedildi.'}, status_code=403)
        if int(request.headers.get('content-length', '0')) > MAX_UPLOAD + 1024 * 1024:
            return JSONResponse({'detail':'Dosya en fazla 25 MB olabilir.'}, status_code=413)
        if request.method in ('POST', 'PUT'):
            original_receive = request._receive
            received = 0
            async def limited_receive():
                nonlocal received
                message = await original_receive()
                received += len(message.get('body', b''))
                if received > MAX_UPLOAD + 1024 * 1024:
                    raise HTTPException(413, 'İstek boyutu aşıldı.')
                return message
            request._receive = limited_receive
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse({'detail':str(exc)}, status_code=400)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        log.exception('request_failed')
        store.error('api', str(exc))
        return JSONResponse({'detail':'İşlem tamamlanamadı. Tanılama sayfasını kontrol edin.'}, status_code=500)

    def get(kind, key):
        value = store.get(kind, key)
        if not value:
            raise HTTPException(404, 'Kayıt bulunamadı.')
        return value

    async def upload(file, folder, max_seconds):
        key = uid()
        source = store.root / folder / f'{key}.upload'
        target = store.root / folder / f'{key}.wav'
        size = 0
        try:
            with source.open('wb') as stream:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, 'Dosya en fazla 25 MB olabilir.')
                    stream.write(chunk)
            metadata = await asyncio.to_thread(convert_audio, source, target, max_seconds)
            return store.add_asset(target, **metadata)
        finally:
            source.unlink(missing_ok=True)
            await file.close()

    @app.get('/api/v1/health')
    async def health():
        return dict(status='ok', version='1.0.0')

    @app.get('/api/v1/system/status')
    async def status():
        return dict(tts=engines.status(), stt={**engines.stt_state,
                    'installed':(ROOT/'.venv-stt/Scripts/python.exe').is_file()},
                    lm=await lm.models(), offline=store.settings()['offline'], network=network.describe(),
                    counts=dict(voices=store.count('voice'), generations=store.count('job'),
                                conversations=store.count('conversation')))

    @app.get('/api/v1/system/gpu')
    async def gpu():
        return {**(await asyncio.to_thread(gpu_status)), **engines.status()}

    @app.get('/api/v1/system/local-ca.crt', include_in_schema=False)
    async def local_certificate():
        certificate = ROOT / 'data/certs/VoiceAIStudio-Local-CA.crt'
        if not network.https_url or not certificate.is_file():
            raise HTTPException(404, 'Yerel HTTPS sertifikası hazır değil.')
        # Only the public CA is downloadable. Private keys have no API route.
        return FileResponse(certificate, media_type='application/x-x509-ca-cert',
                            filename='ASYA-Local-CA.crt')

    @app.get('/api/v1/settings', response_model=Settings)
    async def settings():
        return Settings(**store.settings()).model_dump()

    @app.put('/api/v1/settings', response_model=Settings)
    async def save_settings(body: Settings):
        previous = store.settings()
        if previous['tts_device'] != body.tts_device:
            if engines.gpu_lock.locked() or not engines.queue.empty():
                raise HTTPException(409, 'Cihazı değiştirmeden önce işleri tamamlayın veya iptal edin.')
            async with engines.gpu_lock:
                await engines.blocking(engines.provider.unload)
        store.put('settings', dict(id='app', **body.model_dump()))
        return body

    @app.get('/api/v1/llm/models')
    @app.get('/api/v1/llm/status')
    async def models():
        return await lm.models()

    @app.get('/api/v1/tts/providers')
    async def providers():
        return dict(providers=REGISTRY.describe(),
                    languages=LANGUAGES)

    @app.post('/api/v1/tts/generate', status_code=202, response_model=Job)
    async def generate(body: Generation):
        return engines.submit(body)

    @app.get('/api/v1/tts/jobs/{key}', response_model=Job)
    async def job(key: str):
        return get('job', key)

    @app.post('/api/v1/tts/jobs/{key}/cancel', response_model=Job)
    async def cancel(key: str):
        get('job', key)
        return engines.cancel(key)

    @app.get('/api/v1/tts/history', response_model=list[Job])
    async def history():
        return store.list('job')

    @app.delete('/api/v1/tts/history/{key}')
    async def delete_generation(key: str):
        record = get('job', key)
        if record['status'] in ('queued','running','cancelling'):
            raise HTTPException(409, 'Önce üretimi iptal edin ve tamamlanmasını bekleyin.')
        for asset_id in [record.get('asset_id')] + [s['asset_id'] for s in record['segments']]:
            if asset_id and store.get('asset', asset_id):
                path = store.asset(asset_id)
                path.unlink(missing_ok=True)
                path.with_suffix('.mp3').unlink(missing_ok=True)
                store.delete('asset', asset_id)
        store.delete('job', key)
        return dict(deleted=True)

    @app.post('/api/v1/tts/warmup')
    async def warmup():
        return engines.submit(Generation(text='Merhaba.', language='tr'))

    @app.post('/api/v1/tts/unload')
    async def unload():
        if engines.gpu_lock.locked() or not engines.queue.empty():
            raise HTTPException(409, 'GPU işlem yapıyor. İşlerin tamamlanmasını bekleyin.')
        async with engines.gpu_lock:
            await engines.blocking(engines.provider.unload)
        return engines.status()

    @app.get('/api/v1/voices', response_model=list[Voice])
    async def voices():
        return store.list('voice')

    @app.get('/api/v1/voices/{key}', response_model=Voice)
    async def voice(key: str):
        return get('voice', key)

    @app.post('/api/v1/voices', status_code=201, response_model=Voice)
    async def create_voice(file: UploadFile = File(...), name: str = Form(..., min_length=1, max_length=80),
                           consent: bool = Form(...), language: str = Form('tr')):
        if not consent:
            raise HTTPException(400, 'Bu sesi kullanma hakkınızı veya izninizi onaylayın.')
        if not name.strip():
            raise HTTPException(400, 'Profil adı boş olamaz.')
        if language not in LANGUAGES:
            raise HTTPException(400, 'Desteklenmeyen dil.')
        asset = await upload(file, 'voices', 60)
        return store.put('voice', dict(name=name.strip(), language=language, asset_id=asset['id'],
                                      duration=asset['duration'], sample_rate=asset['sample_rate'],
                                      consent=True, exaggeration=.5, cfg_weight=.5))

    @app.put('/api/v1/voices/{key}', response_model=Voice)
    async def update_voice(key: str, body: VoiceUpdate):
        return store.put('voice', {**get('voice', key), **body.model_dump()})

    @app.delete('/api/v1/voices/{key}')
    async def delete_voice(key: str):
        record = get('voice', key)
        if any(j.get('voice_id') == key and j['status'] in ('queued','running','cancelling') for j in store.list('job')):
            raise HTTPException(409, 'Bu ses aktif üretimde kullanılıyor.')
        path = store.asset(record['asset_id'])
        path.unlink(missing_ok=True)
        path.with_suffix('.mp3').unlink(missing_ok=True)
        store.delete('asset', record['asset_id'])
        store.delete('voice', key)
        settings = store.settings()
        if settings['default_voice'] == key:
            store.put('settings', {**settings, 'id':'app', 'default_voice':''})
        return dict(deleted=True)

    @app.get('/api/v1/audio/{key}')
    async def audio(key: str, format: str = 'wav'):
        source = store.asset(key)
        if format not in ('wav', 'mp3'):
            raise HTTPException(400, 'Desteklenen biçimler: wav, mp3')
        if format == 'mp3':
            target = source.with_suffix('.mp3')
            if not target.is_file():
                await asyncio.to_thread(export_mp3, source, target)
            source = target
        return FileResponse(source, media_type='audio/mpeg' if format == 'mp3' else 'audio/wav',
                            filename=f'voice-{key}.{format}')

    @app.get('/api/v1/audio/{key}/peaks')
    async def waveform(key: str):
        return dict(peaks=await asyncio.to_thread(peaks, store.asset(key)))

    @app.post('/api/v1/audio/recordings', status_code=201)
    async def recording(file: UploadFile = File(...)):
        return await upload(file, 'recordings', 120)

    stt_slots = asyncio.Semaphore(2)

    @app.post('/api/v1/stt/transcribe')
    async def transcribe(file: UploadFile = File(...), language: str = Form('tr')):
        if language not in LANGUAGES + ['auto']:
            raise HTTPException(400, 'Desteklenmeyen dil.')
        if stt_slots.locked():
            raise HTTPException(429, 'STT kuyruğu dolu.')
        async with stt_slots:
            asset = await upload(file, 'recordings', 120)
            return {**(await engines.transcribe(store.asset(asset['id']), None if language == 'auto' else language)),
                    'asset_id':asset['id']}

    @app.get('/api/v1/stt/status')
    async def stt_status():
        return {**engines.stt_state, 'installed':(ROOT/'.venv-stt/Scripts/python.exe').is_file(),
                'model':store.settings()['stt_model'], 'process_mode':'persistent_isolated_worker'}

    @app.post('/api/v1/stt/unload')
    async def unload_stt():
        if engines.active == 'stt':
            raise HTTPException(409, 'STT işlemi devam ediyor.')
        async with engines.gpu_lock:
            await engines.unload_stt()
        return engines.stt_state

    @app.get('/api/v1/conversations')
    async def conversations():
        return [{k:v for k,v in c.items() if k != 'messages'} | {'message_count':len(c['messages'])}
                for c in store.list('conversation')]

    @app.post('/api/v1/conversations', status_code=201)
    async def create_conversation(body: ConversationCreate):
        return store.put('conversation', dict(title=body.title, messages=[]))

    @app.get('/api/v1/conversations/{key}')
    async def conversation(key: str):
        return get('conversation', key)

    @app.delete('/api/v1/conversations/{key}')
    async def delete_conversation(key: str):
        get('conversation', key)
        if key in chat.busy:
            raise HTTPException(409, 'Önce konuşmayı durdurun.')
        store.delete('conversation', key)
        return dict(deleted=True)

    @app.post('/api/v1/llm/chat')
    async def llm_chat(body: Chat, request: Request):
        async def stream():
            queue = asyncio.Queue(maxsize=100)
            cancel = asyncio.Event()
            async def emit(value):
                await queue.put(value)
            async def run():
                try:
                    await chat.turn(body, emit, cancel)
                except Exception as exc:
                    await emit(dict(type='error', message=str(exc)))
                finally:
                    await queue.put(None)
            task = asyncio.create_task(run())
            try:
                while True:
                    value = await queue.get()
                    if value is None:
                        break
                    yield 'data: ' + json.dumps(value, ensure_ascii=False) + '\n\n'
            finally:
                cancel.set()
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control':'no-cache'})

    @app.websocket('/api/v1/realtime/voice')
    async def realtime(ws: WebSocket):
        if ws.headers.get('origin') not in network.origins | {None} or ws.url.hostname not in network.hosts or ws.headers.get('sec-fetch-site') == 'cross-site':
            await ws.close(code=1008)
            return
        await ws.accept()
        task = None
        preparation = None
        cancel = asyncio.Event()
        jobs = []
        active_request = None

        async def stop_response():
            current, current_jobs = task, list(jobs)
            cancel.set()
            if current and not current.done():
                current.cancel()
                await asyncio.gather(current, return_exceptions=True)
            for key in current_jobs:
                engines.cancel(key)

        async def stop_preparation():
            if preparation and not preparation.done():
                preparation.cancel()
                await asyncio.gather(preparation, return_exceptions=True)

        async def turn(data, request_id, event, turn_jobs):
            try:
                body = Chat.model_validate({k:v for k,v in data.items() if k in Chat.model_fields})
                await chat.turn(body, ws.send_json, event, request_id=request_id, jobs=turn_jobs)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                store.error('chat', str(exc))
                await ws.send_json(dict(type='error', message=str(exc), request_id=request_id))

        async def start_response(data, request_id):
            nonlocal task, cancel, jobs, active_request
            await stop_response()
            cancel = asyncio.Event()
            jobs = []
            active_request = request_id
            task = asyncio.create_task(turn(data, request_id, cancel, jobs))

        async def prepare_audio(data, request_id):
            try:
                await ws.send_json(dict(type='state',state='transcribing',request_id=request_id))
                result = await engines.transcribe(store.asset(data['asset_id']), store.settings()['language'])
                if not result['text'].strip():
                    await ws.send_json(dict(type='ignored',reason='speech_not_detected',request_id=request_id))
                    return
                await ws.send_json(dict(type='transcript',request_id=request_id,**result))
                # Noise/silence must never cancel a valid answer. Replace it only
                # once speech has actually been decoded, or on explicit interrupt.
                await start_response({**data,'text':result['text']},request_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                store.error('chat',str(exc))
                await ws.send_json(dict(type='error',message=str(exc),request_id=request_id))

        try:
            while True:
                data = await ws.receive_json()
                if not isinstance(data, dict):
                    continue
                if len(json.dumps(data)) > 16000:
                    await ws.send_json(dict(type='error',message='Mesaj boyutu aşıldı.'))
                    continue
                kind = data.get('type')
                if kind not in ('interrupt','message','audio'):
                    continue
                await stop_preparation()
                if kind == 'interrupt':
                    await stop_response()
                    await ws.send_json(dict(type='state', state='interrupted', request_id=active_request))
                else:
                    request_id = str(data.get('request_id') or uid())[:100]
                    if kind == 'audio':
                        preparation = asyncio.create_task(prepare_audio(data, request_id))
                    else:
                        await start_response(data, request_id)
        except WebSocketDisconnect:
            pass
        finally:
            await stop_preparation()
            await stop_response()

    @app.get('/api/v1/diagnostics')
    async def diagnostics():
        return dict(benchmarks=store.list('benchmark'), errors=store.list('error'),
                    tts=engines.status(), stt=engines.stt_state)

    frontend = ROOT / 'apps/frontend/dist'
    if frontend.is_dir():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')
    return app


app = create_app()
