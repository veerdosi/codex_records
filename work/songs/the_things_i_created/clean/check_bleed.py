from pathlib import Path
import sys
import numpy as np
from scipy import signal
import soxr
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from dsp import SR, load

s=12000
def band(path):
    x=soxr.resample(load(path).mean(1),SR,s)
    return signal.sosfilt(signal.butter(2,[230,2500],fs=s,btype='bandpass',output='sos'),x)

dirty=band(HERE/'wonder_vocal_bus.wav')
studio=band(HERE/'studio_aligned.wav')
raw=band(HERE.parent/'wonder.wav')

def reference(t,n):
    offsets=np.array([0., 10.03267, 20.06534])
    base=t%10.03267
    centers=np.rint((base+offsets)*s).astype(int)
    return [raw[c-150:c+n+150] for c in centers if c>=150]

def compare(q,z):
    xc=signal.correlate(z,q,mode='valid',method='fft')
    e=np.r_[0,np.cumsum(z*z,dtype='float64')]
    cc=xc/np.sqrt(np.sum(q*q)*np.maximum(e[len(q):]-e[:-len(q)],1e-10))
    j=int(np.argmax(cc))
    return j,float(cc[j]),float(xc[j]/max(e[j+len(q)]-e[j],1e-10))

n=round(.45*s)
rows=[]
for t in np.arange(156.5,195.04,.20):
    j=round((t-154.5)*s)
    d=dirty[j:j+n]
    v=studio[j:j+n]
    matches=[(compare(d,q),q) for q in reference(t,n)]
    if not matches:
        continue
    (peak,corr,scale),ref=max(matches,key=lambda m:m[0][1])
    if corr>.25:
        r=ref[peak:peak+n]
        old=np.dot(d,r)/np.linalg.norm(d)/np.linalg.norm(r)
        new=np.dot(v,r)/max(np.linalg.norm(v)*np.linalg.norm(r),1e-9)
        if np.sqrt(np.mean(v*v))>.002:
            rows.append((round(t,2),round(float(old),3),round(float(new),3)))
print('Matched overlapping sample windows:',len(rows))
print('time, original normalized correlation, replacement normalized correlation')
for row in rows:
    print(*row)
print('median original/clean correlation',np.median(np.abs(np.asarray(rows)[:,1:]),axis=0))
