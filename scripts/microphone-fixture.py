"""Create a browser fake-device WAV from a real generated sample, with VAD silence."""
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from apps.backend.app.core import Store
store=Store()
source=next(j for j in store.list('job') if j.get('status')=='completed' and 'ikinci deneme' in j['text'])
audio,sr=sf.read(store.asset(source['asset_id']))
resampled=np.interp(np.arange(int(len(audio)*48000/sr))*sr/48000,np.arange(len(audio)),audio)
result=np.concatenate([np.zeros(4800),resampled,np.zeros(48000*3)])
sf.write(store.root/'recordings/browser-microphone-fixture.wav',result,48000,subtype='PCM_16')
