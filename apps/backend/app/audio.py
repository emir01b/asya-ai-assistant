from __future__ import annotations

import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
import imageio_ffmpeg

MAX_UPLOAD = 25 * 1024 * 1024


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
