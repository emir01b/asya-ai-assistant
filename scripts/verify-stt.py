import asyncio
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from apps.backend.app.core import Store
from apps.backend.app.engines import Engines

async def main():
    store=Store()
    engines=Engines(store)
    results=[]
    try:
        jobs=[j for j in store.list('job') if j.get('status')=='completed']
        path=store.asset(jobs[0]['asset_id']) if jobs else ROOT/'chatterbox/referans_pcm.wav'
        for index in range(2):
            result=await engines.transcribe(path,'tr')
            results.append(result)
            print(json.dumps(result,ensure_ascii=True),flush=True)
            if result['device']!='cuda':raise RuntimeError('CUDA doğrulanamadı')
            if not result['text'].strip():raise RuntimeError('Transkripsiyon boş')
        if not results[1]['model_reused']:raise RuntimeError('STT model reuse başarısız')
        (ROOT/'docs/real-stt-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        await engines.close()

asyncio.run(main())
