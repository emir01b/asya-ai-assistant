"""Isolated STT process. Keeps CTranslate2 dependencies out of the TTS environment."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# torch's existing CUDA 12/cuDNN DLLs; never replace torch or CUDA packages.
DLL_HANDLES = []
torch_lib = ROOT / '.venv/Lib/site-packages/torch/lib'
if os.name == 'nt' and torch_lib.is_dir():
    os.environ['PATH'] = str(torch_lib) + os.pathsep + os.environ.get('PATH', '')
    DLL_HANDLES.append(os.add_dll_directory(str(torch_lib)))


MODEL = None
MODEL_KEY = None


def transcribe_request(path, model_name, device, language, offline, fallback):
    global MODEL, MODEL_KEY
    os.environ['HF_HUB_OFFLINE'] = str(offline)
    from faster_whisper import WhisperModel
    from huggingface_hub import constants as hf_constants
    hf_constants.HF_HUB_OFFLINE = str(offline) == '1'
    start = time.perf_counter()
    warning = None

    def transcribe(target):
        global MODEL, MODEL_KEY
        key = (model_name, target, str(offline))
        reused = MODEL is not None and MODEL_KEY == key
        if not reused:
            if MODEL is not None:
                MODEL.model.unload_model()
                MODEL = None
            MODEL = WhisperModel(model_name, device=target, compute_type='float16' if target == 'cuda' else 'int8',
                                 local_files_only=str(offline) == '1', cpu_threads=4, num_workers=1,
                                 download_root=str(ROOT/'data/models/stt'))
            MODEL_KEY = key
        loaded = time.perf_counter()
        segments, info = MODEL.transcribe(path, language=None if language == 'auto' else language,
                                         vad_filter=True, beam_size=3,temperature=0,
                                         condition_on_previous_text=False,
                                         vad_parameters=dict(min_speech_duration_ms=200,
                                                             min_silence_duration_ms=300,speech_pad_ms=250))
        result = [dict(start=s.start, end=s.end, text=s.text,avg_logprob=s.avg_logprob,
                       no_speech_prob=s.no_speech_prob) for s in segments
                  if not (s.no_speech_prob>.6 and s.avg_logprob<-1.0)]
        return result, info, loaded-start, reused

    try:
        segments, info, load, reused = transcribe(device)
    except RuntimeError as exc:
        if device != 'cuda' or str(fallback) != '1':
            raise
        warning = f'GPU STT başarısız; CPU kullanılıyor ve daha yavaş olabilir: {exc}'
        device = 'cpu'
        segments, info, load, reused = transcribe(device)
    return dict(text=' '.join(s['text'].strip() for s in segments), segments=segments,
          language=info.language, seconds=time.perf_counter()-start, load_seconds=load,
          device=device, warning=warning, model_reused=reused)


def main():
    if sys.argv[1:] == ['--serve']:
        for line in sys.stdin:
            try:
                params = json.loads(line)
                result = transcribe_request(**params)
            except Exception as exc:
                result = {'error':str(exc)}
            print(json.dumps(result, ensure_ascii=True), flush=True)
    else:
        print(json.dumps(transcribe_request(*sys.argv[1:]), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
