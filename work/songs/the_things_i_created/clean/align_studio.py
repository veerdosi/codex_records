from pathlib import Path
import sys
import numpy as np
from scipy import signal, ndimage
import soundfile as sf

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from dsp import SR, load, filt

ref=load(HERE/'studio.wav').mean(axis=1)
bus=load(HERE/'wonder_vocal_bus.wav').mean(axis=1)
origin=154.5
reference=filt(ref,'bandpass',(210,3200))
target=filt(bus,'bandpass',(210,3200))
matches=[]
for time in np.arange(156.55,195.45,.38):
    i=round((time-origin)*SR)
    expected=round((time+1.39716-.0001374*time)*SR)
    q=target[i:i+round(.35*SR)]
    margin=round(.0075*SR)
    r=reference[expected-margin:expected+len(q)+margin]
    cross=signal.correlate(r,q,mode='valid',method='fft')
    e=np.r_[0,np.cumsum(r*r,dtype='float64')]
    corr=cross/np.sqrt(np.sum(q*q)*np.maximum(e[len(q):]-e[:-len(q)],1e-10))
    j=int(np.argmax(corr))
    if corr[j]>.74 and 0<j<len(corr)-1:
        a,b,c=corr[j-1:j+2]
        fraction=.5*(a-c)/(a+c-2*b)
        matches.append((origin+i/SR,(expected+j-margin+fraction)/SR,float(corr[j])))

a,b,weight=np.asarray(matches).T
slope,intercept=np.polyfit(a,b,1,w=weight)
residual=b-(slope*a+intercept)
keep=np.abs(residual)<.00019
slope,intercept=np.polyfit(a[keep],b[keep],1,w=weight[keep])
residual=b[keep]-(slope*a[keep]+intercept)
assert keep.sum()>65 and np.max(abs(residual))<.00020
t=origin+np.arange(len(bus))/SR
aligned=ndimage.map_coordinates(ref,[(t*slope+intercept)*SR],order=3)
sf.write(HERE/'studio_aligned.wav',np.repeat(aligned[:,None],2,axis=1),SR,subtype='FLOAT')
print('Matched',keep.sum(),'of',len(matches),'windows; rate',slope,'intercept',intercept)
print('Residual ms max',np.max(abs(residual))*1000,'median correlation',np.median(weight[keep]))
