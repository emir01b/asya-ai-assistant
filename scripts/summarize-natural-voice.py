"""Validate a completed natural-voice benchmark without regenerating audio."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics

import numpy as np
import soundfile as sf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--pitch', action='store_true', help='Analyze reference and first balanced raw/paced pair with pYIN.')
    args = parser.parse_args()
    root = args.directory.resolve()
    assert root.is_dir(), root
    data = json.loads((root / 'measurements.json').read_text(encoding='utf8'))
    rows = data['rows']
    assert Counter(r['kind'] for r in rows) == {'mode': 36, 'matrix': 9, 'comparison': 1}

    def finite(value):
        if isinstance(value, dict):
            for key, item in value.items():
                assert not (key in ('error', 'scoring_error') and item), (key, item)
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
        elif isinstance(value, float):
            assert math.isfinite(value), value

    finite(data)
    checked = {}

    def audio(path):
        path = path.resolve()
        assert path.is_file(), path
        assert path.is_relative_to(root), path
        if str(path) not in checked:
            samples, rate = sf.read(path, dtype='float32')
            assert samples.size > 0 and rate > 0 and np.isfinite(samples).all(), path
            checked[str(path)] = {'duration_seconds': len(samples) / rate,
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        return checked[str(path)]

    modes = [r for r in rows if r['kind'] == 'mode']
    matrix = [r for r in rows if r['kind'] == 'matrix']
    assert len({r['text'] for r in modes}) == 12
    for row in modes + matrix:
        for variant in ('raw', 'paced'):
            actual = audio(root / row[variant]['file'])
            assert abs(actual['duration_seconds'] - row[variant]['duration_seconds']) < 1e-3
        assert row['metrics']['first_audio_seconds'] > 0
        assert row['metrics']['total_seconds'] >= row['metrics']['first_audio_seconds']

    comparison = next(r for r in rows if r['kind'] == 'comparison')
    candidates = comparison['candidates']
    assert len(candidates) == 2 and comparison['selected_candidate'] in (0, 1)
    store = root / 'store'
    with sqlite3.connect((store / 'database/studio.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        def asset(key):
            record = db.execute("SELECT body FROM records WHERE kind='asset' AND id=?", (key,)).fetchone()
            assert record, key
            return store / json.loads(record[0])['path']

        for candidate in candidates:
            score = candidate['scoring']
            assert score['transcript'].strip() and 0 <= score['fidelity'] <= 1
            assert math.isfinite(score['speaker_similarity'])
            audio(asset(candidate['asset_id']))
            for segment in candidate['segments']:
                audio(asset(segment['asset_id']))
        jobs = [json.loads(r[0]) for r in db.execute("SELECT body FROM records WHERE kind='job'")]
        assert len(jobs) == 47 and all(j['status'] == 'completed' for j in jobs)
        errors = db.execute("SELECT count(*) FROM records WHERE kind='error'").fetchone()[0]
        assert errors == 0, errors

    # Verify every browser listening asset and its mapping, including randomized pairs.
    import re
    for html_name, expected in [('paired-listening.html', 24), ('blind-listening.html', 90)]:
        sources = re.findall(r'<audio controls src="([^"]+)"', (root / html_name).read_text(encoding='utf8'))
        assert len(sources) == expected
        for source in sources:
            audio(root / source)
    for entry in json.loads((root / 'paired-key.json').read_text(encoding='utf8')):
        assert audio(root / f"pair-{entry['pair']:02d}-{entry['label']}.wav")['sha256'] == audio(root / entry['source'])['sha256']
    for index, entry in enumerate(json.loads((root / 'blind-key.json').read_text(encoding='utf8')), 1):
        assert audio(root / f'blind-{index:03d}.wav')['sha256'] == audio(root / entry['source'])['sha256']

    timings = {mode: {key: statistics.median(r['metrics'][key] for r in modes if r['mode'] == mode)
                       for key in ('first_audio_seconds', 'total_seconds', 'rtf')}
               for mode in ('fast', 'balanced', 'quality')}
    hashes = [{'exaggeration': r['exaggeration'], 'cfg_weight': r['cfg_weight'], 'seed': r['seed'],
               'sha256': audio(root / r['raw']['file'])['sha256']} for r in matrix]
    same_pair_count = sum(len({audio(root / r['raw']['file'])['sha256'] for r in modes
                              if r['text'] == text and r['mode'] in ('balanced', 'quality')}) == 1
                          for text in {r['text'] for r in modes})
    reference_duration = audio(store / 'voices/reference.wav')['duration_seconds']
    summary = {'device': data['device'], 'row_counts': dict(Counter(r['kind'] for r in rows)),
               'completed_jobs_including_warmup': len(jobs), 'recorded_errors': errors,
               'validated_wav_count': len(checked), 'warm_mode_medians': timings,
               'matrix_raw_hashes': hashes, 'matrix_distinct_raw_hashes': len({h['sha256'] for h in hashes}),
               'balanced_quality_identical_pairs': same_pair_count,
               'comparison': comparison,
               'reference_duration_seconds': reference_duration}
    if args.pitch:
        import librosa
        pitch = {}
        first = next(r for r in modes if r['mode'] == 'balanced')
        for name, path in [('reference', store / 'voices/reference.wav'),
                           ('first_balanced_raw', root / first['raw']['file']),
                           ('first_balanced_paced', root / first['paced']['file'])]:
            samples, rate = sf.read(path, dtype='float32')
            f0, voiced, _ = librosa.pyin(samples, fmin=65, fmax=500, sr=rate,
                                        frame_length=1024, hop_length=256)
            values = f0[voiced & np.isfinite(f0)]
            assert values.size > 0
            pitch[name] = {'p10_hz': float(np.percentile(values, 10)),
                           'median_hz': float(np.median(values)), 'p90_hz': float(np.percentile(values, 90)),
                           'voiced_frames': len(values), 'duration_seconds': len(samples) / rate}
        summary['pitch_example'] = pitch
    (root / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('comparison', 'matrix_raw_hashes')}, indent=2))


if __name__ == '__main__':
    main()
