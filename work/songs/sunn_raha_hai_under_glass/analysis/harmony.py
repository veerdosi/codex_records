from pathlib import Path
import sys
import librosa
import numpy as np
from scipy import signal
import soundfile as sf
NAMES='C Db D Eb E F Gb G Ab A Bb B'.split()
ROOT=Path(__file__).resolve().parent.parent
args=sys.argv[1:]
wav=Path(args[0]) if args else ROOT/'sources/source.wav'
sr=22050
x=librosa.load(wav,sr=sr)[0]
hop=256
a=librosa.midi_to_hz(24)
q=np.abs(librosa.cqt(x,sr=sr,fmin=a,n_bins=84,hop_length=hop,tuning=None))
t=np.arange(q.shape[1])*hop/sr
mid=q[24:72].reshape(4,12,-1)
low=q[:36].reshape(3,12,-1)
harm=(mid**.8).sum(axis=0)
bass=(low[:2]**1.4).sum(axis=0)
classes=np.arange(12)
patterns=[]
for r in range(12):
    for label,c in [('',[0,4,7]),('m',[0,3,7]),('sus4',[0,5,7]),('7',[0,4,7,10]),('m7',[0,3,7,10]),('dim',[0,3,6])]:
        m=np.full(12,-.35)
        m[(np.array(c)+r)%12]=1
        m[r]=1.15
        patterns.append((r,label,m))

def read(lo,hi):
    keep=(t>=lo+.05)&(t<hi-.07)
    b=bass[:,keep].mean(axis=1)
    h=harm[:,keep].mean(axis=1)
    b=b/b.max()
    h=h/h.max()
    def score(k):
        r,label, m=k
        return np.dot(m,h)+1.8*b[r]-.47*(label in ['7','m7'])
    best=sorted(patterns,key=score,reverse=True)[:3]
    return ' '.join(NAMES[r]+label for r,label,_ in best), ''.join(NAMES[k]+' ' for k in np.argsort(b)[-3:][::-1]), ''.join(NAMES[k]+' ' for k in np.argsort(h)[-4:][::-1])

B=60/85.42
phase=.408
def when(b):
    return phase+B*b
for bar in range(78):
    v=when(bar*4)
    a,c,d=read(v,v+B*2)
    e,f,g=read(v+B*2,v+B*4)
    print(f'{bar:02} {v:6.2f} | {a:18s} {c:9s} {d:12s} | {e:18s} {f:9s} {g:12s}')
np.savez(ROOT/'analysis'/('harmony-'+wav.stem+'.npz'),t=t,cqt=q,bass=bass,harm=harm)
