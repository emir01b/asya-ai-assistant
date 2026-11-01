"""Reproducible Turkish voice experiment; quality requires human blind listening.

Example: .venv/Scripts/python.exe scripts/benchmark-natural-voice.py --output data/verification/natural-voice/smoke --smoke
Full run: 12 texts x 3 modes, 3 x 3 parameter matrix, and two-candidate STT.
Live database is opened read-only solely for consented reference metadata.
"""
from __future__ import annotations
import argparse
import html
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import librosa
import numpy as np
import soundfile as sf
from apps.backend.app.core import DEFAULTS
from apps.backend.app.audio import pace_audio
from apps.backend.app.engines import ChatterboxProvider

TEXTS = [
    'Merhaba! Bugün nasılsın? İstersen önce seni dinleyeyim, ardından birlikte uygun bir yol bulalım.',
    'Bunu birlikte adım adım çözebiliriz.',
    'İstersen önce seni dinleyeyim, sonra seçeneklere bakalım.',
    'Bu akşam hava biraz serin; yanına bir ceket almayı unutma.',
    'Dr. Ayşe ile 12.11.2026 tarihinde saat 13.30 için görüşmemiz var, hazırlanmaya başlayabilirsin.',
    'Üç küçük adım atmak, hiç başlamamaktan çok daha iyidir.',
    'Şu anda emin değilim ama birlikte kontrol edebiliriz.',
    'Ne güzel bir haber! Senin adına çok sevindim.',
    'Bu sorunun cevabı sandığımızdan daha karmaşık olabilir.',
    'Lütfen pencereyi kapatır mısın? Dışarıdan çok ses geliyor.',
    'Bugün biraz yorgun hissediyorsan kendine zaman ayır.',
    'Merhaba! Önce durumu birlikte inceleyelim. Bilgisayarı yeniden başlatmadan önce açık belgelerini kaydetmeni öneririm, çünkü beklenmedik bir kapanma yaptığın değişikliklerin kaybolmasına neden olabilir. Ardından ayarları kontrol ederiz ve sorun devam ederse bir sonraki adımı beraber belirleriz.'
]

def stats(samples, sr):
    samples = np.asarray(samples, dtype=np.float32)
    pitches, voiced, _ = librosa.pyin(samples, fmin=65, fmax=500, sr=sr, frame_length=1024, hop_length=256)
    pitches = pitches[voiced & np.isfinite(pitches)]
    return dict(duration_seconds=len(samples)/sr, peak=float(np.max(np.abs(samples))),
                rms=float(np.sqrt(np.mean(samples ** 2))),
                pitch_median_hz=float(np.median(pitches)) if len(pitches) else None, pitch_p10_hz=float(np.percentile(pitches,10)) if len(pitches) else None, pitch_p90_hz=float(np.percentile(pitches,90)) if len(pitches) else None, voiced_frames=int(len(pitches)))

async def run(args):
    import asyncio, shutil, sqlite3
    import torch
    from apps.backend.app.core import Store
    from apps.backend.app.engines import Engines
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Read only consented metadata, never construct Store on the live database.
    uri = (ROOT / 'data/database/studio.sqlite3').resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        records = [json.loads(row[0]) for row in db.execute("select body from records where kind='voice'")]
        voice = next(v for v in records if v.get('name') == args.voice and v.get('consent'))
        aid = voice.get('reference_asset_id') or voice['asset_id']
        asset = json.loads(db.execute("select body from records where kind='asset' and id=?", (aid,)).fetchone()[0])
    src = (ROOT / 'data' / asset['path']).resolve(strict=True)
    if not src.is_relative_to((ROOT / 'data').resolve()):
        raise ValueError('Invalid reference path')
    store = Store(root / 'store')
    dst = store.root / 'voices' / 'reference.wav'
    shutil.copyfile(src, dst)
    local_asset = store.add_asset(dst)
    local_voice = store.put('voice', {**voice, 'asset_id':local_asset['id'], 'reference_asset_id':local_asset['id']})
    store.put('settings', dict(id='app', **DEFAULTS))
    engine = Engines(store)
    engine.start()
    rows = []
    async def job(text, mode, seed, exaggeration=.5, cfg=.5, compare=False):
        req = dict(text=text, language='tr', provider='chatterbox', voice_id=local_voice['id'],
            exaggeration=exaggeration, cfg_weight=cfg, seed=seed, speech_quality=mode,
            compare_candidates=compare, speech_rate=1.0, trailing_pause_ms=0, normalize=True)
        submitted = engine.submit(req)
        result = await engine.wait_job(submitted['id'])
        if result['status'] != 'completed':
            raise RuntimeError(str(result))
        return result
    async def save_audio(result, prefix):
        raw, sr = sf.read(store.asset(result['asset_id']), dtype='float32')
        paced = pace_audio(raw, sr, .9, 0)
        files = {}
        for kind, samples in [('raw', raw), ('paced', paced)]:
            path = root / f'{prefix}-{kind}.wav'
            sf.write(path, samples, sr, subtype='PCM_16')
            files[kind] = dict(file=path.name, **stats(samples, sr))
        return files
    def save():
        (root/'measurements.json').write_text(json.dumps(dict(device=torch.cuda.get_device_name(0), offline=True,
            reference_voice=args.voice, rows=rows), ensure_ascii=False, indent=2), encoding='utf8')
    try:
        if not args.smoke:
            warmup = await job('Merhaba, bu bir ısınma örneğidir.', 'balanced', 4199)
            print(f"warmup (excluded from results): {warmup['metrics']}", flush=True)
        corpus = TEXTS[:1] if args.smoke else TEXTS
        modes = ('balanced',) if args.smoke else ('fast','balanced','quality')
        for ti, text in enumerate(corpus):
            for mode in modes:
                result = await job(text, mode, 4200 + ti)
                audio = await save_audio(result, f't{ti:02d}-{mode}')
                rows.append(dict(kind='mode', text=text, mode=mode, seed=4200+ti,
                    metrics=result['metrics'], segments=[s['text'] for s in result['segments']], **audio))
                save(); print(f"mode {ti+1}/{len(corpus)} {mode}: {result['metrics']}", flush=True)
        if not args.smoke:
            for e in (.3,.5,.7):
                for c in (0.,.3,.5):
                    result = await job(TEXTS[2], 'balanced', 4202, e, c)
                    audio = await save_audio(result, f'matrix-e{e:.1f}-c{c:.1f}')
                    rows.append(dict(kind='matrix', text=TEXTS[2], mode='balanced', seed=4202,
                        exaggeration=e, cfg_weight=c, metrics=result['metrics'], **audio))
                    save(); print(f'matrix {e} {c}', flush=True)
            result = await job(TEXTS[2], 'balanced', 4202, compare=True)
            rows.append(dict(kind='comparison', text=TEXTS[2], metrics=result['metrics'],
                candidates=result['candidates'], selected_candidate=result['selected_candidate']))
            save(); print(f"comparison {result['selected_candidate']} {result['candidates']}", flush=True)
        entries = [(r,k) for r in rows if r['kind'] in ('mode','matrix') for k in ('raw','paced')]
        random.Random(8923).shuffle(entries)
        mapping=[]; cards=[]
        for i,(row,kind) in enumerate(entries):
            label=f'Örnek {i+1:03d}'; blind=root/f'blind-{i+1:03d}.wav'
            shutil.copyfile(root/row[kind]['file'],blind)
            mapping.append(dict(label=label, source=row[kind]['file']))
            cards.append(f'<article><h2>{label}</h2><p>{html.escape(row["text"])}</p><audio controls src="{blind.name}"></audio><p>Doğallık / benzerlik / telaffuz / kopukluk: <input placeholder="Notlar"></p></article>')
        # Pair same-text balanced and quality outputs; randomized orientation per pair.
        pairs=[]; pair_key=[]; rng=random.Random(7291)
        mode_rows=[r for r in rows if r['kind']=='mode']
        for ti,text in enumerate(TEXTS):
            chosen=[r for r in mode_rows if r['text']==text and r['mode'] in ('balanced','quality')]
            if len(chosen)!=2: continue
            rng.shuffle(chosen); labels=[]
            for j,r in enumerate(chosen):
                filename=f'pair-{ti+1:02d}-{chr(65+j)}.wav'
                shutil.copyfile(root/r['raw']['file'],root/filename)
                labels.append(f'<label>{chr(65+j)} <audio controls src="{filename}"></audio></label>')
                pair_key.append(dict(pair=ti+1, label=chr(65+j), source=r['raw']['file'], mode=r['mode']))
            pairs.append(f'<article><h2>Çift {ti+1}</h2><p>{html.escape(text)}</p>'+''.join(labels)+'<p>Tercihiniz ve nedeni: <input placeholder="A / B / eşit ve notlar"></p></article>')
        (root/'paired-listening.html').write_text('<meta charset="utf-8"><title>Kör A/B dinleme</title><h1>Aynı metin: kör A/B</h1><p>Dinledikten sonra tercih ve telaffuz, doğallık, benzerlik notlarınızı ayrıca kaydedin. Sayfa kapanınca yazılar kaybolur. Anahtarı test bitince açın.</p>'+''.join(pairs),encoding='utf8')
        (root/'paired-key.json').write_text(json.dumps(pair_key,ensure_ascii=False,indent=2),encoding='utf8')
        (root/'blind-key.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
        (root/'blind-listening.html').write_text('<meta charset="utf-8"><title>Kör dinleme</title><h1>Kör dinleme — deneysel</h1><p>Ölçümler kaliteyi kanıtlamaz; anahtarı değerlendirmeden sonra açın. Notlar sayfa kapatılınca kaybolur.</p>'+''.join(cards),encoding='utf8')
    finally:
        await engine.close()


def main():
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice', default='enes')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    asyncio.run(run(args))

if __name__ == '__main__':
    main()
