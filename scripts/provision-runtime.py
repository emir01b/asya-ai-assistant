"""Installer import/GPU checks, model downloads and first-use settings."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TTS_FILES = [
    've.pt', 't3_mtl23ls_v3.safetensors', 's3gen.pt',
    'grapheme_mtl_merged_expanded_v1.json', 'conds.pt', 'Cangjie5_TC.json',
]


def download_tts():
    os.environ['HF_HUB_OFFLINE'] = '0'
    from huggingface_hub import snapshot_download
    from huggingface_hub import constants
    constants.HF_HUB_OFFLINE = False
    path = Path(snapshot_download('ResembleAI/chatterbox', allow_patterns=TTS_FILES))
    missing = [name for name in TTS_FILES if not (path / name).is_file()]
    if missing:
        raise RuntimeError(f'Model dosyalari eksik: {missing}')
    print(f'TTS modeli hazir: {path}', flush=True)


def check_runtime(device):
    import torch
    import torchaudio
    import torchvision
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    import inspect
    if 't3_model' not in inspect.signature(ChatterboxMultilingualTTS.from_local).parameters:
        raise RuntimeError('Chatterbox V3 API bulunamadi; sabitlenmis kaynak gerekli.')
    print(f'Torch: {torch.__version__}; torchaudio: {torchaudio.__version__}', flush=True)
    if device == 'cuda':
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA kullanilamiyor. NVIDIA surucusunu kontrol edin veya kurucuda CPU secin.')
        # A real kernel also catches unsupported GPU architectures.
        value = (torch.ones(16, device='cuda') * 2).sum().item()
        torch.cuda.synchronize()
        if value != 32:
            raise RuntimeError('GPU hesaplama testi basarisiz.')
        print(f'GPU testi basarili: {torch.cuda.get_device_name(0)}', flush=True)
    else:
        print('CPU modu secildi. CUDA gerekli degil.', flush=True)


def smoke_tts(device):
    from apps.backend.app.engines import ChatterboxProvider
    import soundfile as sf
    engine = ChatterboxProvider()
    try:
        engine.load({'offline': True, 'tts_device': device})
        samples, rate, _, _ = engine.generate('Merhaba, ben Asya.', 'tr', None, .5, .5)
        if len(samples) < rate / 10:
            raise RuntimeError('TTS testi gecerli ses uretmedi.')
        path = ROOT / 'data' / 'setup-test.wav'
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, samples, rate)
        print(f'Turkce TTS testi basarili: {path}', flush=True)
    finally:
        engine.unload()


def check_stt(device):
    from apps.backend.stt_worker import transcribe_request
    result = transcribe_request(str(ROOT / 'data' / 'setup-test.wav'),
                                'large-v3-turbo', device, 'tr', '1', '0')
    if not result['text'].strip():
        raise RuntimeError('STT testi ses dosyasinda konusma bulamadi.')
    print(f"STT testi basarili ({result['device']}): {result['text']}", flush=True)


def initialize_settings(device, online=False):
    from apps.backend.app.core import Store
    store = Store()
    if store.get('settings', 'app') is not None:
        print('Mevcut uygulama ayarlari korundu.', flush=True)
        return
    store.put('settings', dict(id='app', tts_device=device, stt_device=device,
                              offline=not online))
    print(f'Ilk kullanim cihaz ayarlari kaydedildi: {device}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'download', 'smoke', 'stt-check', 'settings'])
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--online', action='store_true')
    args = parser.parse_args()
    if args.command == 'download':
        download_tts()
    elif args.command == 'check':
        check_runtime(args.device)
    elif args.command == 'smoke':
        smoke_tts(args.device)
    elif args.command == 'stt-check':
        check_stt(args.device)
    else:
        initialize_settings(args.device, args.online)


if __name__ == '__main__':
    main()
