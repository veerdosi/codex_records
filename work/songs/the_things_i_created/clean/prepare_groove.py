from pathlib import Path
import sys

import numpy as np
import soundfile as sf

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
sys.path.insert(0,str(PROJECT.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from dsp import SR, load

BAR=240/95
START=37*BAR-.45
END=40*BAR+.50
source=load(PROJECT/'coffee.wav')

def calibrated(name,origin):
    inst=load(PROJECT/f'{name}_instrumental.wav')
    total=inst+load(PROJECT/f'{name}_vocals.wav')
    offset=round(origin*SR)
    raw=source[offset:offset+len(total)]
    gain=np.sum(total*raw)/np.sum(total*total)
    return inst*gain

def take(audio,start,stop,origin):
    i=round((start-origin)*SR)
    return audio[i:i+round((stop-start)*SR)].copy()

early=calibrated('coffee_hook',76)
late=calibrated('coffee_verse',95)
cross_start=95.14
cross_end=95.85
a=take(early,START,cross_end,76)
b=take(late,cross_start,END,95)
n=len(a)-round((cross_start-START)*SR)
ramp=np.sin(np.linspace(0,np.pi/2,n,dtype=np.float32))**2
b[:n]=a[-n:]+(b[:n]-a[-n:])*ramp[:,None]
mix=np.concatenate([a[:-n],b])
sf.write(HERE/'groove_entry.wav',mix,SR,subtype='FLOAT')
