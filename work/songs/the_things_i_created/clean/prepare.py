from pathlib import Path
import numpy as np
import soundfile as sf
import sys

HERE=Path(__file__).resolve().parent
P=HERE.parent
sys.path.insert(0,str(P.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from dsp import SR, load

def samples(t):
    return round(t*SR)

raw=load(P/'wonder.wav')
def estimate(name,origin):
    music=load(P/f'{name}_instrumental.wav')
    mix=music+load(P/f'{name}_vocals.wav')
    a=samples(origin)
    target=raw[a:a+len(mix)]
    scale=float(np.sum(mix*target)/np.sum(mix*mix))
    return music*scale

def crop(x,a,b,origin):
    start=samples(a-origin)
    return x[start:start+samples(b-a)].copy()

a,b,pivot=154.5,197.5,171.75
early=crop(estimate('wonder_grind',151),a,174.65,151)
late=crop(estimate('wonder_verse',169),pivot,b,169)
index=samples(pivot-a)
n=len(early)-index
ramp=(.5-.5*np.cos(np.pi*np.clip(np.arange(n)/(n-.02*SR),0,1)))[:,None].astype('float32')
late[:n]=early[index:] + (late[:n]-early[index:])*ramp
bed=np.concatenate([early[:index],late])
stem=raw[samples(a):samples(a)+len(bed)]-bed
sf.write(HERE/'wonder_vocal_bus.wav',stem,SR,subtype='FLOAT')
