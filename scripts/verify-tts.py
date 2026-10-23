"""Real CUDA verification through the same service used by the HTTP API."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apps.backend.app.core import Store
from apps.backend.app.engines import Engines
from apps.backend.app.schemas import Generation
from apps.backend.app.audio import convert_audio


async def main():
    store = Store()
    engine = Engines(store)
    engine.start()
    # Copy and validate the existing reference, never mutate the original.
    reference = store.root/'voices'/'verification-reference.wav'
    metadata = convert_audio(ROOT/'chatterbox/referans_pcm.wav', reference, 60)
    voices = [v for v in store.list('voice') if v['name'] == 'Yerel test referansı']
    if voices:
        voice = voices[0]
    else:
        asset = store.add_asset(reference, **metadata)
        voice = store.put('voice', dict(name='Yerel test referansı', asset_id=asset['id'],
            language='tr', consent=True, exaggeration=.5, cfg_weight=.5, **metadata))
    try:
        results = []
        for text in ['Merhaba! Ses stüdyosu artık hazır.', 'Bu, Türkçe ses klonlama için ikinci deneme.']:
            job = engine.submit(Generation(text=text, voice_id=voice['id']))
            print('submitted', job['id'], flush=True)
            result = await engine.wait_job(job['id'])
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
            if result['status'] != 'completed':
                raise RuntimeError(result['error'])
        report = ROOT/'docs/real-tts-results.json'
        report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        await engine.close()


if __name__ == '__main__':
    asyncio.run(main())
