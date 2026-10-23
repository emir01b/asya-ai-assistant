"""Real running HTTP/WS backend + LM Studio + CUDA STT/TTS. No model substitutes."""
import json
import time
from pathlib import Path

import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000/api/v1'


def validate(client, events):
    errors = [e for e in events if e['type'] == 'error']
    assert not errors, errors
    assert any(e['type'] == 'token' for e in events), 'No real LLM content'
    assert any(e['type'] == 'audio' for e in events), 'No real TTS audio'
    assert events[-1]['type'] == 'done', 'Response incomplete'
    for event in events:
        if event['type'] == 'audio':
            audio = client.get(BASE + '/audio/' + event['asset_id'])
            audio.raise_for_status()
            assert audio.content[:4] == b'RIFF' and len(audio.content) > 44
            job = client.get(BASE + '/tts/jobs/' + event['job_id']).json()
            assert job['status'] == 'completed', job


def main():
    with httpx.Client(timeout=300, trust_env=False) as client:
        settings = client.get(BASE+'/settings').json()
        status = client.get(BASE+'/llm/status').json()
        assert status['connected'] and settings['llm_model']
        voices = client.get(BASE+'/voices').json()
        voice = next((v for v in voices if v['name'] == 'Yerel test referansı'), voices[0] if voices else None)
        voice_id = voice['id'] if voice else None
        events = []
        started = time.perf_counter()
        with client.stream('POST', BASE+'/llm/chat', json=dict(
            text="Bu bir sesli asistan testidir. Bu konuşmada her yanıtını tek kısa Türkçe cümleyle ver. Şimdi sadece 'Merhaba, sesli asistan hazır.' de.",
            voice_id=voice_id, speak=True)) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith('data: '):
                    event = json.loads(line[6:])
                    events.append(event)
                    if event['type'] != 'token':
                        print('SSE', event['type'], flush=True)
        validate(client, events)
        cid = events[0]['conversation_id']
        print('REAL TEXT -> LLM -> TTS PASS', flush=True)
        fixture = ROOT/'data/recordings/browser-microphone-fixture.wav'
        with fixture.open('rb') as audio:
            response = client.post(BASE+'/audio/recordings', files={'file':('live-input.wav',audio,'audio/wav')})
            response.raise_for_status()
            asset = response.json()
        voice_events = []
        with connect('ws://127.0.0.1:8000/api/v1/realtime/voice', origin='http://127.0.0.1:8000') as ws:
            ws.send(json.dumps(dict(type='audio',asset_id=asset['id'],conversation_id=cid,
                                    request_id='real-lm-validation',voice_id=voice_id,speak=True)))
            while True:
                event = json.loads(ws.recv(timeout=300))
                voice_events.append(event)
                if event['type'] != 'token':
                    print('WS',event['type'],flush=True)
                if event['type'] in ('done','error'):
                    break
        validate(client, voice_events)
        transcript = next(e for e in voice_events if e['type']=='transcript')
        assert transcript['device'] == 'cuda' and transcript['text'].strip()
        history = client.get(BASE+'/conversations/'+cid).json()
        assert len(history['messages']) == 4
        report = dict(lm_url=settings['lm_url'],model=settings['llm_model'],all_models_real=True,
                      input='real TTS WAV through recording upload and WebSocket (not physical microphone)',
                      elapsed_seconds=time.perf_counter()-started,text_events=events,voice_events=voice_events,
                      transcript=transcript,persisted_messages=len(history['messages']))
        (ROOT/'docs/real-lm-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('REAL AUDIO -> CUDA STT -> REAL LM STUDIO -> CUDA TTS PASS',flush=True)
        print(json.dumps(dict(model=settings['llm_model'],text_metrics=events[-1]['message']['metrics'],
                              voice_metrics=voice_events[-1]['message']['metrics']),ensure_ascii=True),flush=True)


if __name__ == '__main__':
    main()
