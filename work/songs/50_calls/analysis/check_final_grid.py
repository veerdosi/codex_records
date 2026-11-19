from pathlib import Path
import json, sys
import numpy as np, soundfile as sf, torch
from beat_this.inference import Audio2Beats

p=Path(__file__).resolve().parent
torch.set_num_threads(4)
model=Audio2Beats(checkpoint_path='small0',device='cpu',dbn=False)
for name in sys.argv[1:]:
    path=p/f'{name}.wav'
    x,sr=sf.read(path,dtype='float32')
    b,d=model(x,sr)
    data={'beats':b.tolist(),'downbeats':d.tolist(),'duration':len(x)/sr}
    (p/f'{name}_grid.json').write_text(json.dumps(data))
    print(name, 'duration',round(len(x)/sr,3),'tempi',[(int(a),round(60/np.median(np.diff(b[(b>=a)&(b<a+18)])),1)) for a in np.arange(5,len(x)/sr-10,20)], 'downbeats',np.round(d[:12],3).tolist(),flush=True)
