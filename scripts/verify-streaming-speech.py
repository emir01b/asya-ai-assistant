"""Real CUDA TTS with gated token input; optionally also verify live LM Studio.

The gated stream deliberately waits for audio before emitting the last words.
It proves overlap deterministically and is explicitly not a real LLM benchmark.
Artifacts use a separate verification store rather than the user's chat history.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apps.backend.app.chat import ChatService
from apps.backend.app.core import Store
from apps.backend.app.engines import Engines
from apps.backend.app.llm import LMClient
from apps.backend.app.schemas import Chat


async def main():
    settings = Store().settings()
    store = Store(ROOT / 'data/verification/streaming-speech')
    store.put('settings', {**settings, 'id': 'app', 'default_voice': ''})
    # Reuse an already consented voice, if one is available, in the isolated store.
    voices = [v for v in Store().list('voice') if v.get('consent')]
    voice_id = None
    if voices:
        from apps.backend.app.audio import convert_audio
        voice = next((v for v in voices if v['id'] == settings['default_voice']), voices[0])
        reference = store.root / 'voices/reference.wav'
        metadata = convert_audio(Store().asset(voice['asset_id']), reference, 60)
        asset = store.add_asset(reference, **metadata)
        voice = store.put('voice', {**voice, 'asset_id': asset['id']})
        voice_id = voice['id']
    engine = Engines(store)
    engine.start()
    report = {'real_tts': True, 'device': settings['tts_device'], 'speech_rate': settings['chat_speech_rate']}

    async def verify(lm, gated=False):
        audio_ready = asyncio.Event()
        events = []
        began = time.perf_counter()

        class GatedTokens:
            async def stream(self, *args):
                yield 'Bunu birlikte adım adım çözebiliriz, '
                await asyncio.wait_for(audio_ready.wait(), 180)
                yield 'önce seni dinleyeceğim. '
                yield 'Sonra sakin sakin devam ederiz.'

        async def emit(event):
            events.append({**event, 'elapsed_seconds': time.perf_counter() - began})
            if event['type'] == 'error':
                raise RuntimeError(event['message'])
            if event['type'] == 'audio':
                audio_ready.set()
                print('audio', round(events[-1]['elapsed_seconds'], 3), event['text'], flush=True)

        await asyncio.wait_for(ChatService(store, GatedTokens() if gated else lm, engine).turn(
            Chat(text='Bana sakin bir yürüyüşü dört kısa cümleyle anlat.', voice_id=voice_id),
            emit, asyncio.Event()), 240)
        assert events[-1]['type'] == 'done'
        audio_events = [e for e in events if e['type'] == 'audio']
        assert audio_events
        last_token = max(e['elapsed_seconds'] for e in events if e['type'] == 'token')
        if gated:
            assert audio_events[0]['elapsed_seconds'] < last_token
        pieces = []
        for event in audio_events:
            samples, sr = sf.read(store.asset(event['asset_id']), dtype='float32')
            assert np.isfinite(samples).all() and np.max(np.abs(samples)) > .001
            job = store.get('job', event['job_id'])
            pause = round(sr * job['trailing_pause_ms'] / 1000)
            assert not pause or np.all(samples[-pause:] == 0)
            pieces.append(samples)
        preview = store.root / 'generations' / ('gated-preview.wav' if gated else 'live-preview.wav')
        sf.write(preview, np.concatenate(pieces), sr)
        return dict(real_llm=not gated, audio_before_last_token=audio_events[0]['elapsed_seconds'] < last_token,
                    preview=str(preview), events=events, metrics=events[-1]['message']['metrics'])

    try:
        report['gated_stream'] = await verify(None, gated=True)
        lm = LMClient(store)
        status = await lm.models()
        if status['connected'] and settings['llm_model']:
            report['live_lm'] = await verify(lm)
        else:
            report['live_lm'] = {'verified': False, 'reason': status['error'] or 'Model seçilmedi.'}
    finally:
        await engine.close()
    (ROOT / 'docs/streaming-speech-results.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('gated_stream', 'live_lm')}, ensure_ascii=True))
    print('REAL TTS + STREAM OVERLAP PASS; live LM:', report['live_lm'].get('real_llm', False), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
