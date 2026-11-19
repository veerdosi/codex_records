from pathlib import Path
import sys
import numpy as np
import soundfile as sf
import torch
from beat_this.inference import Audio2Beats

torch.set_num_threads(4)
p = Path(__file__).resolve().parent
m = Audio2Beats(checkpoint_path=sys.argv[1], device='cpu', dbn=False)
sources = [('hyaena', p/'hyaena.wav', 33, 85), ('coffee', p.parent/'coffee.wav', 85, 154),
           ('wonder', p.parent/'wonder.wav', 148, 200)]
if len(sys.argv)>2:
    sources.append(('export', Path(sys.argv[2]), 5, 118))
for name,path,a,b in sources:
    with sf.SoundFile(path) as f:
        sr=f.samplerate
        f.seek(round(a*sr))
        x=f.read(round((b-a)*sr),dtype='float32')
    beats,downs=m(x,sr)
    print(name,'beats',np.round(beats+a,3).tolist(),flush=True)
    print(name,'downs',np.round(downs+a,3).tolist(),flush=True)
