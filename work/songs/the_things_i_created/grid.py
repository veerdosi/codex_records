from pathlib import Path
import numpy as np,soundfile as sf,soxr
from scipy import signal
P=Path(__file__).resolve().parent
for n,origin,lo,hi,bpm in [('wonder',0,168,197,95.7),('coffee',0,97,153,95),('coffee',0,153,207,95)]:
 with sf.SoundFile(P/f'{n}.wav') as f:
  f.seek(round(lo*f.samplerate));x=soxr.resample(f.read(round((hi-lo)*f.samplerate),dtype='float32').mean(1),f.samplerate,16000)
 for freqs in [(36,147),(2200,7500)]:
  y=signal.sosfilt(signal.butter(2,freqs,fs=16000,output='sos',btype='bandpass'),x)
  h=40;k=len(y)//h;e=np.sqrt(np.mean(y[:k*h].reshape(-1,h)**2,axis=1))
  z=np.log(np.maximum(e,np.percentile(e,85)*.035)); flux=np.maximum(z[4:]-z[:-4],0)
  pk=signal.find_peaks(flux,distance=34,prominence=.22)[0]
  t=lo+(pk+2)*h/16000; w=flux[pk]*np.sqrt(e[pk+2])
  div=60/bpm/2
  edges=np.linspace(0,div,65); counts,_=np.histogram(t%div,bins=edges,weights=w)
  print(n,lo,freqs,'phase',[(round((edges[j]+edges[j+1])/2,4),round(counts[j]/counts.sum(),3)) for j in np.argsort(counts)[-4:][::-1]])
  print([(round(t[i],3),round(float(w[i]),2)) for i in sorted(np.argsort(w)[-34:])])
