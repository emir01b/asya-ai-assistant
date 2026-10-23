from __future__ import annotations

import asyncio
import time

from .core import uid, now
from .llm import speech_text, completed_context
from .schemas import Generation
from .prompts import conversation_prompt
from .streaming_speech import SpeechChunker, pause_after


class ChatService:
    def __init__(self, store, lm, engines):
        self.store, self.lm, self.engines = store, lm, engines
        self.busy: set[str] = set()

    async def turn(self, request, emit, cancel, request_id=None, jobs=None):
        started = time.perf_counter()
        request_id = request_id or uid()
        jobs = jobs if jobs is not None else []
        conversation = self.store.get('conversation', request.conversation_id) if request.conversation_id else None
        if request.conversation_id and not conversation:
            raise ValueError('Konuşma bulunamadı.')
        if not conversation:
            conversation = self.store.put('conversation', dict(title=request.text[:60], messages=[]))
        cid = conversation['id']
        if cid in self.busy:
            raise ValueError('Bu konuşmada bir yanıt zaten üretiliyor.')
        self.busy.add(cid)
        assistant = None
        consumer = None
        first_token = None
        first_audio = None

        async def event(kind, **values):
            if not cancel.is_set():
                await emit(dict(type=kind, request_id=request_id, session_id=cid, **values))

        async def speak(queue):
            nonlocal first_audio
            while True:
                text = await queue.get()
                if text is None or cancel.is_set():
                    return
                clean = speech_text(text)
                if not clean:
                    continue
                await event('state', state='synthesizing')
                job = self.engines.submit(Generation(text=clean, voice_id=request.voice_id,
                    language=settings['language'], min_segment_chars=60,
                    speech_rate=settings['chat_speech_rate'], trailing_pause_ms=pause_after(clean)))
                jobs.append(job['id'])
                delivered = 0
                while not cancel.is_set():
                    current = self.store.get('job', job['id'])
                    for segment in current['segments'][delivered:]:
                        if first_audio is None:
                            first_audio = time.perf_counter()-started
                        await event('audio', job_id=job['id'], **segment)
                        delivered += 1
                    if current['status'] in ('completed','cancelled','failed'):
                        if current['status'] == 'failed':
                            await event('error', message=current['error'])
                        break
                    await asyncio.sleep(.08)
                if cancel.is_set():
                    self.engines.cancel(job['id'])
                    return

        async def enqueue(queue, text):
            if cancel.is_set():
                return
            put = asyncio.create_task(queue.put(text))
            try:
                done, _ = await asyncio.wait([put, consumer], return_when=asyncio.FIRST_COMPLETED)
                if consumer in done:
                    await consumer  # Propagate TTS errors rather than deadlocking a full queue.
                    if not put.done():
                        return  # A cancelled consumer will no longer drain a full queue.
                await put
            finally:
                if not put.done():
                    put.cancel()
                    await asyncio.gather(put, return_exceptions=True)

        try:
            user = dict(id=uid(), role='user', content=request.text.strip(), created_at=now())
            conversation['messages'].append(user)
            self.store.put('conversation', conversation)
            await event('start', conversation_id=cid, user=user)
            await event('state', state='thinking')
            settings = self.store.settings()
            messages = [dict(role='system', content=conversation_prompt(settings['system_prompt'], request.speak))]
            # Bound context; interrupted assistant messages aren't sent as complete answers.
            messages += completed_context(conversation['messages'][-60:])
            queue = asyncio.Queue(maxsize=16)
            consumer = asyncio.create_task(speak(queue)) if request.speak else None
            assistant = dict(id=uid(), role='assistant', content='', created_at=now(), job_ids=jobs)
            chunker = SpeechChunker()
            async for token in self.lm.stream(messages, request.model):
                if cancel.is_set():
                    break
                if first_token is None:
                    first_token = time.perf_counter()-started
                assistant['content'] += token
                await event('token', token=token, message_id=assistant['id'])
                if consumer:
                    for chunk in chunker.feed(token):
                        await enqueue(queue, chunk)
            if not assistant['content'].strip() and not cancel.is_set():
                raise ValueError('Model boş yanıt döndürdü. Modeli veya konuşma bağlamını kontrol edin.')
            if consumer:
                if not cancel.is_set():
                    for chunk in chunker.finish():
                        await enqueue(queue, chunk)
                await enqueue(queue, None)
                await consumer
            assistant['interrupted'] = cancel.is_set()
            assistant['metrics'] = dict(llm_first_token_seconds=first_token, first_audio_seconds=first_audio,
                                        total_seconds=time.perf_counter()-started)
            conversation['messages'].append(assistant)
            self.store.put('conversation', conversation)
            self.store.put('benchmark', dict(source='chat', conversation_id=cid, **assistant['metrics']))
            await event('done', message=assistant)
        except asyncio.CancelledError:
            cancel.set()
            if assistant:
                assistant['interrupted'] = True
                conversation['messages'].append(assistant)
                self.store.put('conversation', conversation)
            raise
        except Exception:
            cancel.set()
            if assistant and assistant['content']:
                assistant['interrupted'] = True
                conversation['messages'].append(assistant)
                self.store.put('conversation', conversation)
            raise
        finally:
            self.busy.discard(cid)
            if consumer and not consumer.done():
                consumer.cancel()
                await asyncio.gather(consumer, return_exceptions=True)
            if cancel.is_set():
                for key in jobs:
                    self.engines.cancel(key)
