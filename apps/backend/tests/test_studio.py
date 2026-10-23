from __future__ import annotations

import asyncio
import io
import json
import tempfile
import threading
import time
import sys
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from apps.backend.app.core import Store
from apps.backend.app.engines import Engines
from apps.backend.app.llm import LMClient, speech_text, split_sentences, completed_context
from apps.backend.app.main import create_app
from apps.backend.app.schemas import Generation, Settings


def wav_bytes(seconds=1):
    data = io.BytesIO()
    sf.write(data, np.sin(np.arange(int(24000*seconds))*.03).astype('float32')*.1, 24000, format='WAV')
    return data.getvalue()


class FakeProvider:
    def __init__(self, delay=.025, error=None):
        self.model = None
        self.device = 'cpu'
        self.load_seconds = .01
        self.loads = 0
        self.calls = 0
        self.parallel = 0
        self.max_parallel = 0
        self.delay, self.error = delay, error
        self.entered = threading.Event()

    def load(self, settings):
        if self.model is None:
            self.model = object()
            self.loads += 1

    def generate(self, *args):
        self.calls += 1
        self.parallel += 1
        self.max_parallel = max(self.parallel, self.max_parallel)
        self.entered.set()
        try:
            time.sleep(self.delay)
            if self.error:
                raise RuntimeError(self.error)
            return np.zeros(2400, dtype=np.float32), 24000, self.delay, None
        finally:
            self.parallel -= 1

    def unload(self):
        self.model = None


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.provider = FakeProvider()
        self.app = create_app(self.store, self.provider)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.tmp.cleanup()

    def wait(self, key):
        deadline = time.monotonic()+5
        while time.monotonic()<deadline:
            result = self.client.get('/api/v1/tts/jobs/'+key).json()
            if result['status'] in ('completed','cancelled','failed'):
                return result
            time.sleep(.02)
        self.fail('job timeout')

    def voice(self):
        return self.client.post('/api/v1/voices', data=dict(name='Test voice',consent='true'),
             files={'file':('misleading.mp4',wav_bytes(),'application/octet-stream')})

    def test_health_and_openapi(self):
        self.assertEqual(self.client.get('/api/v1/health').json()['status'],'ok')
        paths = self.client.get('/openapi.json').json()['paths']
        self.assertIn('/api/v1/stt/transcribe',paths)

    def test_origin_and_host_rejected(self):
        self.assertEqual(self.client.get('/api/v1/settings', headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/v1/health',headers={'Host':'evil.example'}).status_code,403)

    def test_oversized_upload_rejected_before_decode(self):
        self.assertEqual(self.client.post('/api/v1/voices',headers={'Content-Length':str(28*1024*1024)},content=b'x').status_code,413)

    def test_settings_persist_and_remote_url_rejected(self):
        settings = self.client.get('/api/v1/settings').json()
        settings['system_prompt']='Kalıcı ayar'
        self.assertEqual(self.client.put('/api/v1/settings',json=settings).status_code,200)
        self.assertEqual(Store(Path(self.tmp.name)).settings()['system_prompt'],'Kalıcı ayar')
        settings['lm_url']='https://external.example/v1'
        self.assertEqual(self.client.put('/api/v1/settings',json=settings).status_code,422)

    def test_voice_decode_rename_and_delete(self):
        response = self.voice()
        self.assertEqual(response.status_code,201,response.text)
        voice = response.json()
        self.assertAlmostEqual(voice['duration'],1,places=2)
        self.assertEqual(voice['sample_rate'],24000)
        renamed = self.client.put('/api/v1/voices/'+voice['id'],json=dict(name='Yeni ad')).json()
        self.assertEqual(renamed['name'],'Yeni ad')
        self.assertEqual(self.client.get('/api/v1/audio/'+voice['asset_id']).headers['content-type'],'audio/wav')
        self.assertEqual(len(self.client.get('/api/v1/audio/'+voice['asset_id']+'/peaks').json()['peaks']),160)
        self.assertEqual(self.client.delete('/api/v1/voices/'+voice['id']).status_code,200)
        self.assertEqual(self.client.get('/api/v1/voices/'+voice['id']).status_code,404)

    def test_bad_audio_and_missing_consent(self):
        bad = self.client.post('/api/v1/voices',data=dict(name='Bad',consent='true'),files={'file':('fake.wav',b'not audio','audio/wav')})
        self.assertEqual(bad.status_code,400)
        no_consent = self.client.post('/api/v1/voices',data=dict(name='No',consent='false'),files={'file':('voice.wav',wav_bytes(),'audio/wav')})
        self.assertEqual(no_consent.status_code,400)
        self.assertEqual(len(self.store.list('voice')),0)

    def test_generate_with_reference_history_mp3_and_delete(self):
        voice = self.voice().json()
        response = self.client.post('/api/v1/tts/generate',json=dict(text='Merhaba. İkinci cümle.',voice_id=voice['id']))
        self.assertEqual(response.status_code,202)
        job = self.wait(response.json()['id'])
        self.assertEqual(job['status'],'completed',job)
        self.assertEqual(len(job['segments']),2)
        self.assertGreater(job['metrics']['duration'],.2)
        self.assertEqual(self.provider.loads,1)
        mp3 = self.client.get('/api/v1/audio/'+job['asset_id']+'?format=mp3')
        self.assertEqual(mp3.status_code,200)
        self.assertEqual(mp3.headers['content-type'],'audio/mpeg')
        self.assertEqual(len(self.client.get('/api/v1/tts/history').json()),1)
        self.assertEqual(self.client.delete('/api/v1/tts/history/'+job['id']).status_code,200)

    def test_form_validation_and_missing_voice(self):
        for body in [dict(text='  '),dict(text='hi',language='xx'),dict(text='hi',exaggeration=4)]:
            self.assertEqual(self.client.post('/api/v1/tts/generate',json=body).status_code,422)
        self.assertEqual(self.client.post('/api/v1/tts/generate',json=dict(text='hi',voice_id='../missing')).status_code,400)

    def test_audio_traversal(self):
        self.store.put('asset',dict(id='escape',path='../../secret.wav'))
        self.assertEqual(self.client.get('/api/v1/audio/escape').status_code,400)

    def test_conversations_crud(self):
        c=self.client.post('/api/v1/conversations',json=dict(title='Test')).json()
        self.assertEqual(self.client.get('/api/v1/conversations/'+c['id']).json()['messages'],[])
        self.assertEqual(len(self.client.get('/api/v1/conversations').json()),1)
        self.assertEqual(self.client.delete('/api/v1/conversations/'+c['id']).status_code,200)

    def test_llm_unavailable_is_visible(self):
        async def unavailable():
            raise ValueError('LM Studio kapalı')
            yield ''
        with patch.object(self.app.state.lm,'stream',side_effect=lambda *args:unavailable()):
            response=self.client.post('/api/v1/llm/chat',json=dict(text='Merhaba',speak=False))
            self.assertIn('LM Studio kapalı',response.text)

    def test_sse_chat_stream_persists_and_produces_audio(self):
        async def stream(*args):
            for token in ['Merhaba! ', 'Size nasıl ', 'yardımcı olabilirim?']:
                yield token
                await asyncio.sleep(.005)
        with patch.object(self.app.state.lm,'stream',stream):
            response=self.client.post('/api/v1/llm/chat',json=dict(text='Selam',speak=True))
        events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        self.assertTrue(any(e['type']=='token' for e in events))
        self.assertTrue(any(e['type']=='audio' for e in events))
        self.assertEqual(events[-1]['type'],'done')
        cid=events[0]['conversation_id']
        self.assertEqual(len(self.client.get('/api/v1/conversations/'+cid).json()['messages']),2)

    def test_chat_tts_queue_failure_returns_instead_of_deadlocking(self):
        async def stream(*args):
            for _ in range(30):
                yield 'Bir cümle. '
                await asyncio.sleep(.001)
        with patch.object(self.app.state.lm,'stream',stream), patch.object(self.app.state.engines,'submit',side_effect=ValueError('Kuyruk dolu')):
            response=self.client.post('/api/v1/llm/chat',json=dict(text='Selam',speak=True))
            self.assertIn('Kuyruk dolu',response.text)

    def test_llm_failure_cancels_already_submitted_speech(self):
        async def stream(*args):
            yield 'Bu yanıtın ilk cümlesi ses kuyruğuna girecek kadar uzun. '
            await asyncio.sleep(.02)
            raise ValueError('LLM bağlantısı kesildi')
        self.provider.delay=.2
        with patch.object(self.app.state.lm,'stream',stream):
            response=self.client.post('/api/v1/llm/chat',json=dict(text='Selam',speak=True))
        self.assertIn('kesildi',response.text)
        for j in self.store.list('job'):
            self.assertIn(j['status'],('cancelling','cancelled'))

    def test_websocket_request_ids_and_interrupt(self):
        async def stream(*args):
            for token in ['Birinci ', 'yanıt. ', 'Devam.']:
                yield token
                await asyncio.sleep(.02)
        with patch.object(self.app.state.lm,'stream',stream):
            with self.client.websocket_connect('/api/v1/realtime/voice') as ws:
                ws.send_json(dict(type='message',text='Bir',request_id='old',speak=False))
                event=ws.receive_json()
                self.assertEqual(event['request_id'],'old')
                ws.send_json(dict(type='message',text='İki',request_id='new',speak=False))
                new_seen=False
                for _ in range(25):
                    e=ws.receive_json()
                    if e.get('request_id')=='new':new_seen=True
                    if new_seen:self.assertEqual(e.get('request_id'),'new')
                    if e['type']=='done':break
                self.assertTrue(new_seen)

    def test_stt_error_is_reported(self):
        async def fake(*args):
            raise ValueError('STT model önbelleği eksik')
        with patch.object(self.app.state.engines,'transcribe',fake):
            r=self.client.post('/api/v1/stt/transcribe',files={'file':('x.wav',wav_bytes(),'audio/wav')})
            self.assertEqual(r.status_code,400)
            self.assertIn('önbelleği',r.json()['detail'])

    def test_silent_audio_does_not_cancel_an_in_progress_reply(self):
        async def stream(*args):
            yield 'Yanıt '
            await asyncio.sleep(.15)
            yield 'tamamlandı.'
        async def silence(*args):
            return dict(text='',segments=[],device='cpu')
        path=self.store.root/'recordings/silent.wav'
        path.write_bytes(wav_bytes())
        asset=self.store.add_asset(path)
        with patch.object(self.app.state.lm,'stream',stream),patch.object(self.app.state.engines,'transcribe',silence):
            with self.client.websocket_connect('/api/v1/realtime/voice') as ws:
                ws.send_json(dict(type='message',text='Test',request_id='reply',speak=False))
                self.assertEqual(ws.receive_json()['type'],'start')
                ws.send_json(dict(type='audio',asset_id=asset['id'],request_id='noise',speak=False))
                ignored=False;finished=False
                while not (ignored and finished):
                    event=ws.receive_json()
                    self.assertNotEqual(event['type'],'error')
                    if event['type']=='ignored':ignored=True
                    if event['type']=='done':
                        finished=True
                        self.assertEqual(event['request_id'],'reply')
                        self.assertEqual(event['message']['content'],'Yanıt tamamlandı.')

    def test_emoji_is_visible_in_text_but_never_creates_a_tts_job(self):
        async def stream(*args):
            for token in ['İyiyim, teşekkür ederim. ','😊']:
                yield token
        with patch.object(self.app.state.lm,'stream',stream):
            response=self.client.post('/api/v1/llm/chat',json=dict(text='Nasılsın?',speak=True))
        self.assertIn('😊',response.text)
        self.assertEqual(len(self.store.list('job')),1)
        self.assertEqual(self.store.list('job')[0]['text'],'İyiyim, teşekkür ederim.')


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name))
        self.provider=FakeProvider(.12)
        self.engine=Engines(self.store,self.provider)
        self.engine.start()

    async def asyncTearDown(self):
        await self.engine.close()
        self.tmp.cleanup()

    async def test_concurrent_jobs_are_serial_and_model_loads_once(self):
        jobs=[self.engine.submit(Generation(text='Merhaba.')) for _ in range(4)]
        results=await asyncio.gather(*(self.engine.wait_job(j['id']) for j in jobs))
        self.assertTrue(all(j['status']=='completed' for j in results))
        self.assertEqual(self.provider.max_parallel,1)
        self.assertEqual(self.provider.loads,1)

    async def test_active_cancellation_retains_gpu_until_segment_finishes(self):
        job=self.engine.submit(Generation(text='Bir. İki. Üç.'))
        await asyncio.to_thread(self.provider.entered.wait,2)
        self.assertEqual(self.engine.cancel(job['id'])['status'],'cancelling')
        self.assertTrue(self.engine.gpu_lock.locked())
        result=await self.engine.wait_job(job['id'])
        self.assertEqual(result['status'],'cancelled')
        self.assertEqual(self.provider.calls,1)

    async def test_queued_cancel_is_not_run(self):
        first=self.engine.submit(Generation(text='Bir.'))
        second=self.engine.submit(Generation(text='İki.'))
        self.engine.cancel(second['id'])
        await self.engine.wait_job(first['id'])
        self.assertEqual((await self.engine.wait_job(second['id']))['status'],'cancelled')
        self.assertEqual(self.provider.calls,1)

    async def test_oom_is_recoverable_and_visible(self):
        self.provider.error='CUDA out of memory'
        job=self.engine.submit(Generation(text='Merhaba'))
        result=await self.engine.wait_job(job['id'])
        self.assertEqual(result['status'],'failed')
        self.assertIn('GPU belleği',result['error'])
        self.assertIsNone(self.provider.model)
        self.provider.error=None
        second=self.engine.submit(Generation(text='Tekrar'))
        self.assertEqual((await self.engine.wait_job(second['id']))['status'],'completed')

    async def test_queue_bound(self):
        for _ in range(16):self.engine.submit(Generation(text='Test'))
        with self.assertRaises(ValueError):self.engine.submit(Generation(text='Taşma'))
        for j in self.store.list('job'):self.engine.cancel(j['id'])

    async def test_stt_pipe_worker_reuses_process_without_async_subprocess(self):
        real_popen = subprocess.Popen
        code = "import sys,json; count=0\nfor line in sys.stdin:\n count+=1\n print(json.dumps(dict(text='test',device='cpu',seconds=.01,segments=[],language='tr',model_reused=count>1)),flush=True)"
        with patch('apps.backend.app.engines.subprocess.Popen', side_effect=lambda args,**kwargs:real_popen([sys.executable,'-u','-c',code] if any('stt_worker.py' in str(a) for a in args) else args,**kwargs)), patch('asyncio.create_subprocess_exec',side_effect=AssertionError('Windows Selector loop cannot use async subprocess')):
            first=await self.engine.transcribe(Path('test.wav'),'tr')
            pid=self.engine.stt_process.pid
            second=await self.engine.transcribe(Path('test.wav'),'tr')
            self.assertFalse(first['model_reused'])
            self.assertTrue(second['model_reused'])
            self.assertEqual(pid,self.engine.stt_process.pid)

    async def test_stt_cancellation_terminates_owned_worker(self):
        real_popen = subprocess.Popen
        code = "import sys,json,time\nfor line in sys.stdin:\n time.sleep(30)\n print('{}',flush=True)"
        with patch('apps.backend.app.engines.subprocess.Popen', side_effect=lambda args,**kwargs:real_popen([sys.executable,'-u','-c',code] if any('stt_worker.py' in str(a) for a in args) else args,**kwargs)):
            task=asyncio.create_task(self.engine.transcribe(Path('test.wav'),'tr'))
            await asyncio.sleep(.1)
            worker=self.engine.stt_process
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            self.assertIsNotNone(worker.poll())
            self.assertFalse(self.engine.gpu_lock.locked())


class UnitTests(unittest.TestCase):
    def test_short_spoken_sentences_are_grouped_without_changing_words(self):
        self.assertEqual(split_sentences('Ne güzel! Nasıl yardımcı olabilirim sana bugün?',min_chars=45),
                         ['Ne güzel! Nasıl yardımcı olabilirim sana bugün?'])
        self.assertEqual(speech_text('😊✨'),'')

    def test_interrupted_user_assistant_pairs_are_not_sent_back_to_llm(self):
        messages=[dict(role='user',content='Bir'),dict(role='assistant',content='Bir yanıt'),
                  dict(role='user',content='Gürültü'),dict(role='assistant',content='',interrupted=True),
                  dict(role='user',content='Gerçek soru')]
        self.assertEqual([m['content'] for m in completed_context(messages)],['Bir','Bir yanıt','Gerçek soru'])
    def test_turkish_segmentation_and_normalization(self):
        self.assertEqual(split_sentences('Dr. Ali geldi. Değer 3.14 oldu!'),['Dr. Ali geldi.','Değer 3.14 oldu!'])
        self.assertTrue(all(len(s)<=240 for s in split_sentences('uzun '*300)))
        self.assertEqual(speech_text('<think>gizli</think> **Merhaba** [dünya](http://local) `test`'),'Merhaba dünya test')
        self.assertNotIn('secret',speech_text('Merhaba. ```secret```'))

    def test_restart_marks_incomplete_jobs_and_keeps_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory))
            job=store.put('job',dict(status='running'))
            store.put('settings',dict(id='app',temperature=.3))
            restarted=Store(Path(directory))
            restarted.recover_jobs()
            self.assertEqual(restarted.get('job',job['id'])['status'],'failed')
            self.assertEqual(restarted.settings()['temperature'],.3)

    def test_lm_rejects_nonlocal_urls(self):
        for url in ['http://evil.com/v1','file:///tmp','http://127.0.0.1@evil.com/v1']:
            with self.assertRaises(ValueError):Settings(lm_url=url)


class LMTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_client_parses_sse(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory));store.put('settings',dict(id='app',llm_model='discovered-model'))
            def handle(request):
                if request.url.path.endswith('/models'):
                    return httpx.Response(200,json={'data':[{'id':'discovered-model'}]})
                return httpx.Response(200,text='data: {"choices":[{"delta":{"content":"Merhaba"}}]}\n\ndata: [DONE]\n\n')
            original=httpx.AsyncClient
            def client(**kwargs):return original(transport=httpx.MockTransport(handle),**kwargs)
            with patch('apps.backend.app.llm.httpx.AsyncClient',side_effect=client):
                lm=LMClient(store)
                self.assertTrue((await lm.models())['connected'])
                self.assertEqual([t async for t in lm.stream([dict(role='user',content='Selam')])],['Merhaba'])

    async def test_connection_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            def handle(request):raise httpx.ConnectError('offline',request=request)
            original=httpx.AsyncClient
            with patch('apps.backend.app.llm.httpx.AsyncClient',side_effect=lambda **kw:original(transport=httpx.MockTransport(handle),**kw)):
                result=await LMClient(Store(Path(directory))).models()
                self.assertFalse(result['connected'])
                self.assertIn('offline',result['error'])


if __name__=='__main__':unittest.main(verbosity=2)
