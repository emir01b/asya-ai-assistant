from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf

from apps.backend.app.audio import pace_audio
from apps.backend.app.chat import ChatService
from apps.backend.app.core import Store
from apps.backend.app.engines import Engines, ChatterboxProvider
from apps.backend.app.llm import speech_text
from apps.backend.app.prompts import VOICE_OUTPUT_PROMPT, conversation_prompt
from apps.backend.app.schemas import Chat, Generation
from apps.backend.app.streaming_speech import SpeechChunker, pause_after
from apps.backend.tests.test_studio import FakeProvider


class ChunkTests(unittest.TestCase):
    def test_short_first_sentence_is_released_before_stream_finishes(self):
        chunker = SpeechChunker()
        self.assertEqual(chunker.feed('Merhaba.'), [])
        self.assertEqual(chunker.feed(' Şimdi'), ['Merhaba.'])
        self.assertEqual(chunker.finish(), ['Şimdi'])

    def test_opening_clause_starts_before_long_sentence_finishes(self):
        chunker = SpeechChunker()
        phrase = 'Bunu birlikte adım adım çözebiliriz,'
        self.assertEqual(chunker.feed(phrase + ' önce'), [phrase])
        self.assertEqual(chunker.feed(' seni dinleyeceğim, sonra devam ederiz.'), [])
        self.assertEqual(chunker.finish(), ['önce seni dinleyeceğim, sonra devam ederiz.'])

    def test_split_hidden_markers_never_leak_and_visible_text_is_not_lost(self):
        text = '<think>Gizli. Düşünce.</think>Merhaba. ```python\nsecret = 3\n``` Devam edelim. Son cümle.'
        expected = 'Merhaba. Devam edelim. Son cümle.'
        for width in range(1, len(text) + 1):
            chunker = SpeechChunker()
            chunks = []
            for start in range(0, len(text), width):
                chunks.extend(chunker.feed(text[start:start + width]))
            chunks.extend(chunker.finish())
            visible = ' '.join(speech_text(c) for c in chunks)
            self.assertEqual(' '.join(visible.split()), expected, width)

    def test_unfinished_hidden_blocks_are_discarded(self):
        for suffix in ['<think>Gizli. Bitmedi.', '```python\nsecret', '<thi']:
            chunker = SpeechChunker()
            chunks = chunker.feed('Yanıt hazır. ' + suffix) + chunker.finish()
            self.assertEqual(' '.join(chunks), 'Yanıt hazır.')

    def test_abbreviations_decimals_and_words_are_kept_intact(self):
        text = 'Dr. Ali ile değer 3.14 ve oran 1,25 hakkında konuşalım. Sonra devam.'
        chunker = SpeechChunker()
        chunks = []
        for token in text:
            chunks.extend(chunker.feed(token))
        chunks += chunker.finish()
        self.assertEqual(chunks[0], text.split(' Sonra')[0])
        self.assertEqual(' '.join(chunks), text)

    def test_unpunctuated_text_is_released_without_waiting_for_the_end(self):
        chunker = SpeechChunker()
        text = 'sözcük ' * 100
        chunks = chunker.feed(text)
        self.assertGreater(len(chunks), 1)
        chunks += chunker.finish()
        self.assertEqual(' '.join(chunks).split(), text.split())
        self.assertTrue(all(len(c) <= 240 for c in chunks))

    def test_date_or_list_number_does_not_become_an_isolated_audio_chunk(self):
        for text in ['Bugün 19. Ekim ve hava güzel. ', '1. Önce seni dinleyelim. ', 'A. Yılmaz bugün geldi. ']:
            chunker = SpeechChunker()
            chunks = []
            for token in text:
                chunks.extend(chunker.feed(token))
            self.assertEqual(chunks, [text.strip()])

    def test_prompt_preserves_personality_and_text_only_behavior(self):
        custom = 'Sen Zehra adında sıcak bir asistansın.'
        self.assertEqual(conversation_prompt(custom, False), custom)
        self.assertEqual(conversation_prompt(custom, True), custom + '\n\n' + VOICE_OUTPUT_PROMPT)
        self.assertEqual(pause_after('Hazırsan,'), 140)
        self.assertEqual(pause_after('Hazır mısın?”'), 280)


class PacingTests(unittest.TestCase):
    def test_reference_conditioning_is_reused_and_invalidated_when_switching(self):
        provider = ChatterboxProvider()
        provider.model = MagicMock()
        provider.model.generate.return_value.squeeze.return_value.cpu.return_value.numpy.return_value = np.zeros(2400)
        provider.model.sr = 24000
        provider.device = 'cpu'
        provider.default_conditions = 'default'
        with tempfile.TemporaryDirectory() as directory, patch.dict('sys.modules', torch=MagicMock()):
            reference = Path(directory) / 'ref.wav'
            reference.write_bytes(b'reference')
            for text in ['Merhaba,', 'seni dinliyorum.']:
                provider.generate(text, 'tr', str(reference), .5, .5)
            self.assertEqual(provider.model.prepare_conditionals.call_count, 1)
            provider.generate('Varsayılan.', 'tr', None, .5, .5)
            self.assertEqual(provider.model.conds, 'default')
            provider.generate('Tekrar.', 'tr', str(reference), .5, .5)
            self.assertEqual(provider.model.prepare_conditionals.call_count, 2)
            reference.write_bytes(b'new reference')
            provider.generate('Yeni referans.', 'tr', str(reference), .5, .5)
            self.assertEqual(provider.model.prepare_conditionals.call_count, 3)
            self.assertIsNone(provider.model.generate.call_args.kwargs['audio_prompt_path'])

    def test_real_tempo_filter_slows_audio_without_lowering_pitch(self):
        sr = 24000
        samples = (.15 * np.sin(2 * np.pi * 440 * np.arange(sr * 2) / sr)).astype('float32')
        output = pace_audio(samples, sr, .8, 140)
        voice = output[:-round(sr * .14)]
        self.assertAlmostEqual(len(voice) / sr, 2.5, delta=.08)
        frequency = np.argmax(np.abs(np.fft.rfft(voice))) * sr / len(voice)
        self.assertAlmostEqual(frequency, 440, delta=3)
        self.assertTrue(np.all(output[-round(sr * .14):] == 0))


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.engine = Engines(self.store, FakeProvider())
        self.engine.start()

    async def asyncTearDown(self):
        await self.engine.close()
        self.tmp.cleanup()

    async def test_audio_is_delivered_while_llm_is_still_streaming(self):
        audio_ready = asyncio.Event()
        self.store.put('settings', dict(id='app', speech_quality='fast'))
        events, prompts = [], []

        class SlowLM:
            async def stream(inner, messages, model):
                prompts.extend(messages)
                yield 'Bunu birlikte adım adım çözebiliriz, '
                # If the implementation waits for the final answer, this times out.
                await asyncio.wait_for(audio_ready.wait(), 5)
                yield 'önce seni dinleyeceğim.'

        async def emit(event):
            events.append(event)
            if event['type'] == 'audio':
                audio_ready.set()

        await asyncio.wait_for(ChatService(self.store, SlowLM(), self.engine).turn(
            Chat(text='Konuşalım'), emit, asyncio.Event(), request_id='stream-test'), 10)
        first_audio = next(i for i, e in enumerate(events) if e['type'] == 'audio')
        last_token = max(i for i, e in enumerate(events) if e['type'] == 'token')
        self.assertLess(first_audio, last_token)
        self.assertEqual(events[-1]['type'], 'done')
        self.assertIn(VOICE_OUTPUT_PROMPT, prompts[0]['content'])
        audio = [e for e in events if e['type'] == 'audio']
        self.assertEqual([e['text'] for e in audio],
                         ['Bunu birlikte adım adım çözebiliriz,', 'önce seni dinleyeceğim.'])
        self.assertTrue(all(e['request_id'] == 'stream-test' for e in events))
        self.assertEqual([self.store.get('job', e['job_id'])['trailing_pause_ms'] for e in audio], [140, 280])
        self.assertTrue(all(self.store.get('job', e['job_id'])['speech_rate'] == .9 for e in audio))

    async def test_saved_audio_has_the_same_pacing_as_streamed_segments(self):
        job = self.engine.submit(Generation(text='Birinci cümle. İkinci cümle.', speech_rate=.9, trailing_pause_ms=280))
        result = await self.engine.wait_job(job['id'])
        self.assertEqual(result['status'], 'completed')
        pieces = [sf.read(self.store.asset(s['asset_id']))[0] for s in result['segments']]
        combined, _ = sf.read(self.store.asset(result['asset_id']))
        np.testing.assert_array_equal(combined, np.concatenate(pieces))

    async def test_cancel_after_early_audio_does_not_synthesize_the_tail(self):
        cancel = asyncio.Event()
        events = []

        class LM:
            async def stream(inner, *args):
                yield 'Merhaba. '
                while not cancel.is_set():
                    await asyncio.sleep(.01)
                yield 'Bu bölüm seslendirilmemeli.'

        async def emit(event):
            events.append(event)
            if event['type'] == 'audio':
                cancel.set()

        await asyncio.wait_for(ChatService(self.store, LM(), self.engine).turn(
            Chat(text='Selam'), emit, cancel), 5)
        self.assertEqual(len(self.store.list('job')), 1)
        self.assertEqual(self.store.list('job')[0]['text'], 'Merhaba.')
        self.assertFalse(any(e['type'] == 'done' for e in events))

    async def test_cancel_with_full_speech_queue_finishes_without_deadlocking(self):
        self.engine.provider.delay = .2
        cancel = asyncio.Event()

        class LM:
            async def stream(inner, *args):
                yield ('Bu cümle ses kuyruğunu doldurmak için yeterli uzunlukta bir açıklama içeriyor. ' * 40)

        async def emit(event):
            pass

        task = asyncio.create_task(ChatService(self.store, LM(), self.engine).turn(
            Chat(text='Uzun yanıt'), emit, cancel))
        await asyncio.wait_for(asyncio.to_thread(self.engine.provider.entered.wait), 2)
        await asyncio.sleep(.02)
        cancel.set()
        await asyncio.wait_for(task, 2)
        self.assertEqual(len(self.store.list('job')), 1)
