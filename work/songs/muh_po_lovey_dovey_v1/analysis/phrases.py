import librosa, numpy as np, soundfile as sf, scipy.signal as sg, sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]
for n in sys.argv[1:]:
 g={'farebi':('htdemucs_ft',2.6666667,0.008),'namastute':('htdemucs',3.,.322)}
 model,bar,phase=g[n]
 source=p/'stems/demucs'/model/n
 x,sr=sf.read(source/'other.wav',dtype='float32')
 z,sr=sf.read(source/'bass.wav',dtype='float32')
 v,sr=sf.read(source/'vocals.wav',dtype='float32')
 f,sr=sf.read(source/'drums.wav',dtype='float32')
 def chrom(x,minmidi,n_bins):
  return np.abs(librosa.cqt(sg.resample_poly(x.mean(1),1,4),sr=sr//4,hop_length=256,fmin=librosa.midi_to_hz(minmidi),n_bins=n_bins))
 def pitch(c,t,u,n=3):
  a=c[:,int(t*sr/1024):int(u*sr/1024)].mean(1)
  b=a.reshape(-1,12).sum(0)
  return ' '.join('C C# D D# E F F# G G# A Bb B'.split()[i]+str(round(100*b[i]/b.sum())) for i in np.argsort(b)[-n:][::-1])
 c=chrom(x,36,60); d=chrom(z,24,36)
 print(n,'time | vocal | drums | bass | pitched backing')
 for i in range(int((len(x)/sr-phase)/bar)):
  t=phase+i*bar;u=t+bar; a,b=int(t*sr),int(u*sr)
  print('%2d %6.2f %5.1f %5.1f %7s %s'%(i,t,20*np.log10(np.sqrt(np.mean(v[a:b]**2))+1e-9),20*np.log10(np.sqrt(np.mean(f[a:b]**2))+1e-9),pitch(d,t,u,2),pitch(c,t,u,5)))
