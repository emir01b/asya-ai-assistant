"""Real STT and TTS; LM Studio replaced only in this explicitly labelled test."""
import asyncio
import json
import sys
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from apps.backend.app.core import Store
from apps.backend.app.engines import Engines
from apps.backend.app.chat import ChatService
from apps.backend.app.schemas import Chat

class TestLLM:
    async def stream(self,*args):
        for token in ['Merhaba, ', 'Türkçe sesli yanıt testi başarılı.']:
            yield token
            await asyncio.sleep(.03)

async def main():
    source_store=Store()
    store=Store(ROOT/'data/verification/pipeline')
    engine=Engines(store)
    engine.start()
    try:
        source=next(j for j in source_store.list('job') if j.get('status')=='completed' and 'ikinci deneme' in j['text'])
        audio_path=store.root/'recordings/input.wav'
        shutil.copy2(source_store.asset(source['asset_id']),audio_path)
        old_voice=source_store.get('voice',source['voice_id'])
        voice_path=store.root/'voices/reference.wav'
        shutil.copy2(source_store.asset(old_voice['asset_id']),voice_path)
        asset=store.add_asset(voice_path)
        voice=store.put('voice',{**old_voice,'asset_id':asset['id']})
        stt=await engine.transcribe(audio_path,'tr')
        events=[]
        async def emit(event):
            events.append(event)
            print(event['type'],flush=True)
        service=ChatService(store,TestLLM(),engine)
        await service.turn(Chat(text=stt['text'],voice_id=voice['id'],speak=True),emit,asyncio.Event())
        assert any(e['type']=='audio' for e in events)
        assert events[-1]['type']=='done'
        result=dict(stt=stt,lm='MOCK: actual LM Studio unavailable',events=events)
        (ROOT/'docs/pipeline-test-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('REAL STT + MOCK LLM + REAL TTS: PASS',flush=True)
    finally:
        await engine.close()

asyncio.run(main())
