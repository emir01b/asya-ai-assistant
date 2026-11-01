from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from apps.backend.app.core import Store
from apps.backend.app.engines import Engines
from apps.backend.app.main import create_app
from apps.backend.app.schemas import Generation
from apps.backend.tests.test_studio import FakeProvider


class ComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.provider = FakeProvider(delay=0)
        self.engine = Engines(self.store, self.provider)
        self.engine.start()

    async def asyncTearDown(self):
        await self.engine.close()
        self.tmp.cleanup()

    async def test_cancel_during_scoring_never_exposes_audio(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def scoring(*args):
            started.set()
            await release.wait()
            return {'text': 'Merhaba'}
        self.engine._transcribe_locked = scoring
        job = self.engine.submit(Generation(text='Merhaba', compare_candidates=True, seed=12))
        await asyncio.wait_for(started.wait(), 5)
        self.engine.cancel(job['id'])
        release.set()
        result = await asyncio.wait_for(self.engine.wait_job(job['id']), 5)
        self.assertEqual(result['status'], 'cancelled')
        self.assertIsNone(result['asset_id'])
        self.assertEqual(result['segments'], [])
        self.assertEqual(result['candidates'], [])
        self.assertEqual(list((self.store.root / 'generations').glob('*.wav')), [])

    async def test_compare_job_metrics_cover_both_candidates(self):
        self.engine._transcribe_locked = AsyncMock(return_value={'text': 'Merhaba'})
        job = self.engine.submit(Generation(text='Merhaba', compare_candidates=True, seed=4294967295))
        result = await asyncio.wait_for(self.engine.wait_job(job['id']), 5)
        self.assertEqual([c['seed'] for c in result['candidates']], [4294967295, 0])
        self.assertAlmostEqual(result['metrics']['synthesis_seconds'],
                               sum(c['metrics']['synthesis_seconds'] for c in result['candidates']))
        self.assertGreaterEqual(result['metrics']['total_seconds'], result['candidates'][-1]['metrics']['total_seconds'])

    async def test_oom_first_candidate_allows_second(self):
        generate = self.provider.generate
        def fail_first(*args):
            if args[-1] == 12:
                raise RuntimeError('CUDA out of memory')
            return generate(*args)
        self.provider.generate = fail_first
        job = self.engine.submit(Generation(text='Merhaba', compare_candidates=True, seed=12))
        result = await asyncio.wait_for(self.engine.wait_job(job['id']), 5)
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(result['candidates'][0]['seed'], 13)
        self.assertIn('out of memory', result['candidate_errors'][0]['error'])
        self.assertGreaterEqual(self.provider.loads, 2)

    async def test_scoring_failure_falls_back_without_deadlock(self):
        self.engine._transcribe_locked = AsyncMock(side_effect=RuntimeError('STT unavailable'))
        job = self.engine.submit(Generation(text='Merhaba', compare_candidates=True, seed=12))
        result = await asyncio.wait_for(self.engine.wait_job(job['id']), 5)
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(result['selected_candidate'], 0)
        self.assertIn('STT unavailable', result['candidates'][0]['scoring']['error'])
        self.assertFalse(self.engine.gpu_lock.locked())


class SelectionTests(unittest.TestCase):
    def test_selection_preserves_execution_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp))
            app = create_app(store, FakeProvider(delay=0))
            path = store.root / 'generations' / 'selected.wav'
            path.write_bytes(b'audio')
            asset = store.add_asset(path)
            with TestClient(app) as client:
                job = store.put('job', dict(status='completed', text='x', provider='chatterbox',
                    language='tr', voice_id=None, exaggeration=.5, cfg_weight=.5, progress=1, segments=[], error=None, asset_id=asset['id'],
                    metrics=dict(total_seconds=9, synthesis_seconds=6, first_audio_seconds=9, duration=3, rtf=2),
                    candidates=[dict(index=0, seed=1, asset_id=asset['id'], segments=[],
                                     metrics=dict(duration=2, total_seconds=1), scoring=None)]))
                response = client.post('/api/v1/tts/history/' + job['id'] + '/select-candidate', json={'index':0})
                self.assertEqual(response.status_code, 200, response.text)
                metrics = response.json()['metrics']
                self.assertEqual((metrics['total_seconds'], metrics['synthesis_seconds'], metrics['first_audio_seconds']), (9, 6, 9))
                self.assertEqual((metrics['duration'], metrics['rtf']), (2, 3))

    def test_incomplete_job_cannot_select_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp))
            app = create_app(store, FakeProvider(delay=0))
            with TestClient(app) as client:
                job = store.put('job', dict(status='running'))
                response = client.post('/api/v1/tts/history/' + job['id'] + '/select-candidate', json={'index':0})
                self.assertEqual(response.status_code, 409)
