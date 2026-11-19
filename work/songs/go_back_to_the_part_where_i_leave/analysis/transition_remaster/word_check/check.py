from pathlib import Path
import sys
import numpy as np
import soundfile as sf
from scipy import signal
from faster_whisper import WhisperModel
stage=Path(__file__).resolve().parent
root=stage.parents[5]
model=WhisperModel(str(next((root/'work/shared/models/models--Systran--faster-whisper-base.en/snapshots').iterdir())),
                   device='cpu',compute_type='int8',cpu_threads=4)
for key in sys.argv[1:]:
 x,s=sf.read(stage/f'{key} voice proxy.wav',dtype='float32',always_2d=True)
 y=signal.resample_poly(x.mean(axis=1),160,441)
 print(key,flush=True)
 for a,b in [(61.5,65.43),(63,69.7)]:
    clip=y[round((a-56)*16000):round((b-56)*16000)]
    seg,_=model.transcribe(clip,language='en',word_timestamps=True,beam_size=4,
                           condition_on_previous_text=False,no_speech_threshold=.6)
    print(a,b,10*np.log10(np.mean(clip**2)+1e-12),
          [(round(w.start+a,2),round(w.end+a,2),w.word,round(w.probability,2)) for s in seg for w in s.words],
          flush=True)
