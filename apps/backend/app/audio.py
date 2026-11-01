from __future__ import annotations

import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
import imageio_ffmpeg

MAX_UPLOAD = 25 * 1024 * 1024
MAX_VOICE_UPLOAD = 200 * 1024 * 1024


def pace_audio(samples: np.ndarray, sample_rate: int, rate: float, pause_ms: int) -> np.ndarray:
    """Change tempo with FFmpeg atempo (preserving pitch), then add a real pause."""
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if rate != 1.0:
        result = subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error', '-threads', '1',
            '-f', 'f32le', '-ar', str(sample_rate), '-ac', '1', '-i', 'pipe:0',
            '-af', f'atempo={rate:.4f}', '-f', 'f32le', 'pipe:1',
        ], input=samples.astype('<f4').tobytes(), capture_output=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or not result.stdout:
            raise ValueError('Konuşma temposu ayarlanamadı: ' + result.stderr.decode(errors='replace')[:300])
        samples = np.frombuffer(result.stdout, dtype='<f4').copy()
    if pause_ms:
        samples = np.concatenate([samples, np.zeros(round(sample_rate * pause_ms / 1000), dtype=np.float32)])
    return samples


def convert_audio(source: Path, target: Path, max_seconds: float = 120, sample_rate: int = 24000):
    # Decode content rather than trusting a filename; constrain CPU, output length and time.
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error', '-y',
               '-threads', '1', '-protocol_whitelist', 'file,pipe', '-i', str(source),
               '-vn', '-t', str(max_seconds + 1), '-ac', '1', '-ar', str(sample_rate),
               '-c:a', 'pcm_s16le', str(target)]
    result = subprocess.run(command, capture_output=True, timeout=45,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or not target.is_file():
        target.unlink(missing_ok=True)
        raise ValueError('Dosya geçerli ve çözümlenebilir bir ses içermiyor.')
    info = sf.info(target)
    if not 0.25 <= info.duration <= max_seconds:
        target.unlink(missing_ok=True)
        raise ValueError(f'Ses süresi 0,25–{max_seconds:g} saniye olmalı.')
    return dict(duration=info.duration, sample_rate=info.samplerate, channels=info.channels)


def export_mp3(source: Path, target: Path):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error', '-y',
                    '-i', str(source), '-codec:a', 'libmp3lame', '-q:a', '2', str(target)],
                   check=True, capture_output=True, timeout=60,
                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def peaks(path: Path, count=160):
    samples, _ = sf.read(path, dtype='float32', always_2d=True)
    mono = samples.mean(axis=1)
    return [round(float(np.max(np.abs(part))), 4) if part.size else 0
            for part in np.array_split(mono, count)]


def reference_clip(source: Path, target: Path, start: float | None = None, end: float | None = None):
    """Select a short, audible reference without altering its signal."""
    samples, rate = sf.read(source, dtype='float32', always_2d=True)
    mono = samples.mean(axis=1)
    duration = len(mono) / rate
    if start is None and end is None:
        length = min(duration, 8.0)
        width = round(length * rate)
        # Heuristic only: favor audible, varied passages, penalizing silent and clipped
        # frames. This does not identify speech or guarantee a clean recording.
        def score(i):
            window = mono[i:i + width]
            frame_size = max(1, rate // 10)
            frame_rms = np.array([np.sqrt(np.mean(part ** 2)) for part in
                                  (window[j:j + frame_size] for j in range(0, len(window), frame_size))])
            level = float(np.sqrt(np.mean(window ** 2)))
            audible = min(level / .03, 1.0)
            silence = float(np.mean(frame_rms < .003))
            clipping = float(np.mean(np.abs(window) >= .999))
            variation = min(float(np.std(frame_rms)) / .03, 1.0)
            return audible + .3 * variation - silence - min(clipping * 20, 2) - max(0, level - .3)
        offsets = range(0, max(1, len(mono) - width + 1), rate)
        offset = max(offsets, key=score)
        start, end = offset / rate, (offset + width) / rate
    if start is None or end is None or start < 0 or end <= start or end > duration + 1e-7:
        raise ValueError('Referans aralığı ses süresi içinde olmalı.')
    a, b = round(start * rate), min(len(mono), round(end * rate))
    if b <= a or (b - a) / rate < .25:
        raise ValueError('Referans en az 0,25 saniye olmalı.')
    clip = mono[a:b]
    sf.write(target, clip, rate, subtype='PCM_16')
    rms = float(np.sqrt(np.mean(clip ** 2)))
    peak = float(np.max(np.abs(clip)))
    warnings = []
    if rms < 0.003:
        warnings.append('Seçilen referans sessiz veya neredeyse sessiz.')
    elif rms < 0.02:
        warnings.append('Seçilen referansın ses seviyesi düşük.')
    if peak >= 0.999:
        warnings.append('Seçilen referansta kırpılma olabilir.')
    if len(clip) / rate < 6 or len(clip) / rate > 10:
        warnings.append('Referans için 6–10 saniyelik temiz konuşma önerilir.')
    return dict(reference_start=a / rate, reference_end=b / rate, warnings=warnings)
