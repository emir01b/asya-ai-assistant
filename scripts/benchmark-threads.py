"""Measured TTS CPU thread sweep; never changes torch/CUDA package versions."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from apps.backend.app.engines import ChatterboxProvider
from apps.backend.app.core import DEFAULTS

def main():
    import torch
    provider=ChatterboxProvider()
    provider.load(DEFAULTS)
    original=torch.get_num_threads()
    results=[]
    try:
        for index,threads in enumerate((original,original,4,2,original)):
            torch.set_num_threads(threads)
            torch.manual_seed(42)
            samples,sr,elapsed,peak=provider.generate(
                'Merhaba, bugün kendi sesimle Türkçe bir hikâye anlatıyorum.',
                'tr',str(ROOT/'chatterbox/referans_pcm.wav'),.5,.5)
            result=dict(warmup=index==0,threads=threads,seconds=elapsed,duration=len(samples)/sr,rtf=elapsed/(len(samples)/sr),peak_vram_mb=peak)
            print(json.dumps(result),flush=True)
            results.append(result)
        (ROOT/'docs/thread-benchmark.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    finally:
        provider.unload()
        torch.set_num_threads(original)

main()
