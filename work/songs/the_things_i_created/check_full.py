from pathlib import Path
import json
import numpy as np,soundfile as sf
from scipy import signal
P=Path(__file__).resolve().parent
S=44100; B=240/95; C0=196*60/95
r=json.loads((P/'full_report.json').read_text())
m,s=sf.read(P/'what_it_cost_full.wav',dtype='float32')
a,_=sf.read(P/'full_backing_check.wav',dtype='float32')
v,_=sf.read(P/'full_vocal_check.wav',dtype='float32')
assert s==S and m.shape==a.shape==v.shape and np.isfinite(m).all()
def rd(path,x,y):
 with sf.SoundFile(path) as f:
    f.seek(round(x*S))
    return f.read(round((y-x)*S),dtype='float32')
source_full=rd(P/'coffee_verse.wav',0,1)
# Calibrate the stems against their original with the same whole-window fit
# as the renderer and correlate the dry verse at its exact arrangement offset.
import sys
sys.path.insert(0,str(P.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from dsp import load
raw=load(P/'coffee.wav')
tv=load(P/'coffee_remorse_vocals.wav')
ti=load(P/'coffee_remorse_instrumental.wav')
total=tv+ti
orig=raw[round(119*S):round(119*S)+len(total)]
scale=float(np.sum(orig*total)/np.sum(total*total))
def rms(x):
 return 10*np.log10(np.mean(x*x)+1e-12)
def get(x,t,w):
 i=round(t*S);return x[i:i+round(w*S)]
results=[]
for t in np.arange(125.35,143.25,2.1):
 q=get(raw,t,1)-scale*get(ti,t-119,1)
 at=r['travis_verse']+t-C0
 actual=get(v,at-.005,1.01)
 z=signal.correlate(actual[:,0],q[:,0],mode='valid')
 i=int(np.argmax(z))
 corr=float(np.corrcoef(actual[i:i+len(q),0],q[:,0])[0,1])
 shift=i-round(.005*S)
 results.append((round(t,2),shift,round(corr,6)))
 assert abs(shift)<=2 and corr>.997,(t,shift,corr)
print('Travis native vocal time offsets',results)
print('first verse leading silence',rms(get(v,r['kanye_start']-.35,.34)))
print('Kanye last-line ride',rms(get(v,r['kanye_end']-.28,.24)))
for k in ['hook_1','travis_verse','hook_2','strings']:
 t=r[k]
 print(k,round(t,3),'adjacent 1.1s',round(rms(get(m,t-1.15,1.1)),2),round(rms(get(m,t+.04,1.1)),2))
for name,lo,hi in [('Kanye',11.4,26.8),('Travis',40,56),('strings',75,96)]:
 print(name,round(rms(get(m,lo,hi-lo)),2))
