from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    # Explicit setup must download even when the caller normally works offline.
    os.environ['HF_HUB_OFFLINE'] = '0'
    from faster_whisper.utils import download_model
    path = download_model('large-v3-turbo', cache_dir=str(ROOT/'data/models/stt'))
    print(path, flush=True)
