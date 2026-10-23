from pathlib import Path
from faster_whisper.utils import download_model

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    path = download_model('large-v3-turbo', cache_dir=str(ROOT/'data/models/stt'))
    print(path, flush=True)
