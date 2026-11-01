from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

import numpy as np
import soundfile as sf

from apps.backend.app.core import Store
from apps.backend.app.engines import Engines
from apps.backend.app.llm import speech_text
from apps.backend.app.schemas import Generation
from apps.backend.app.schemas import Chat
from apps.backend.app.chat import ChatService
from apps.backend.app.streaming_speech import SpeechChunker
from apps.backend.tests.test_studio import FakeProvider


class QualityChunks(unittest.TestCase):
    def test_language_aware_numbers_and_ambiguous_forms(self):
        self.assertEqual(speech_text('Dr. Ali 1,05 dedi.', 'tr'), 'doktor Ali bir virgül sıfır beş dedi.')
        self.assertEqual(speech_text('Dr. Smith has 42 apples.', 'en'), 'Dr. Smith has 42 apples.')
        self.assertEqual(speech_text('31.10.2026 saat 12:30 ve 1.234', 'tr'),
                         '31.10.2026 saat 12:30 ve 1.234')
        self.assertEqual(speech_text('Toplam 42.', 'tr'), 'Toplam kırk iki.')
        self.assertEqual(speech_text('Kod 001.', 'tr'), 'Kod sıfır sıfır bir.')

    def test_modes_and_boundaries(self):
        text = 'Bunu birlikte adım adım çözebiliriz, önce seni dinleyeceğim. Sonra devam ederiz. '
        fast = SpeechChunker('fast')
        self.assertTrue(fast.feed('Bunu birlikte adım adım çözebiliriz, önce')[0].endswith(','))
        balanced = SpeechChunker('balanced')
        self.assertTrue(balanced.feed(text)[0].endswith('dinleyeceğim.'))
        quality = SpeechChunker('quality')
        self.assertEqual(quality.feed('Merhaba. Devam.'), [])
        self.assertEqual(quality.finish(), ['Merhaba. Devam.'])
        for mode in ('fast', 'balanced', 'quality'):
            c = SpeechChunker(mode)
            self.assertTrue(all(len(x) <= 240 for x in c.feed('kelime ' * 100) + c.finish()))


class QualityJobs(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.provider = FakeProvider(delay=0)
        self.engine = Engines(self.store, self.provider)
        self.engine.start()

    async def asyncTearDown(self):
        await self.engine.close()
        self.tmp.cleanup()

    async def test_profile_override_zero_and_snapshot(self):
        path = self.store.root / 'voices' / 'ref.wav'
        sf.write(path, np.ones(2400) * .1, 24000)
        asset = self.store.add_asset(path)
        voice = self.store.put('voice', dict(name='Test', consent=True, asset_id=asset['id'],
                                            reference_asset_id=asset['id'], reference_start=2,
                                            reference_end=8, exaggeration=.7, cfg_weight=.3))
        job = self.engine.submit(Generation(text='Merhaba.', voice_id=voice['id'], cfg_weight=0))
        self.assertEqual((job['exaggeration'], job['cfg_weight']), (.7, 0))
        self.assertEqual(job['reference_asset_id'], asset['id'])
        self.assertEqual(job['voice_snapshot']['reference_start'], 2)
        self.assertEqual((await self.engine.wait_job(job['id']))['status'], 'completed')

    async def test_chat_keeps_default_voice_and_parameters_for_entire_turn(self):
        path = self.store.root / 'voices' / 'ref.wav'
        sf.write(path, np.ones(2400) * .1, 24000)
        asset = self.store.add_asset(path)
        voice = self.store.put('voice', dict(name='Test', consent=True, asset_id=asset['id'],
                                            exaggeration=.7, cfg_weight=.3))
        self.store.put('settings', {**self.store.settings(), 'id':'app', 'default_voice':voice['id']})
        first_audio = asyncio.Event()
        class LM:
            async def stream(self, *args):
                yield 'Merhaba. '
                await asyncio.wait_for(first_audio.wait(), 5)
                self_store.put('settings', {**self_store.settings(), 'id':'app', 'default_voice':''})
                self_store.put('voice', {**self_store.get('voice', voice['id']), 'exaggeration':1.4})
                yield 'Bu ikinci cümle, aynı sesin kullanıldığını doğrulamak için yeterince uzundur. '
        self_store = self.store
        chat = ChatService(self.store, LM(), self.engine)
        jobs = []
        async def emit(event):
            if event['type'] == 'audio':
                first_audio.set()
        await asyncio.wait_for(chat.turn(Chat(text='Selam'), emit, asyncio.Event(), jobs=jobs), 10)
        self.assertGreaterEqual(len(jobs), 2)
        for key in jobs:
            job = self.store.get('job', key)
            self.assertEqual((job['voice_id'], job['exaggeration'], job['cfg_weight']), (voice['id'], .7, .3))
        self.assertFalse(chat.active_voices)

    async def test_two_candidates_rank_and_distinct_seeds(self):
        self.engine._transcribe_locked = AsyncMock(side_effect=[dict(text='yanlış'), dict(text='Merhaba')])
        job = self.engine.submit(Generation(text='Merhaba', seed=42, compare_candidates=True))
        done = await asyncio.wait_for(self.engine.wait_job(job['id']), 5)
        self.assertEqual(done['status'], 'completed')
        self.assertEqual([x['seed'] for x in done['candidates']], [42, 43])
        self.assertEqual(done['selected_candidate'], 1)
        self.assertEqual(done['asset_id'], done['candidates'][1]['asset_id'])

    async def test_silent_candidate_is_rejected_and_other_retained(self):
        original = self.provider.generate
        self.provider.generate = lambda *a: ((np.zeros(2400), 24000, .01, None)
                                             if a[-1] == 42 else original(*a))
        job = self.engine.submit(Generation(text='Merhaba', seed=42, compare_candidates=True))
        done = await asyncio.wait_for(self.engine.wait_job(job['id']), 5)
        self.assertEqual(done['status'], 'completed')
        self.assertEqual(len(done['candidates']), 1)
        self.assertEqual(done['candidates'][0]['seed'], 43)
        self.assertEqual(len(done['candidate_errors']), 1)
