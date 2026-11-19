"""Compare source and time-stretched transient envelopes at section boundaries."""
from pathlib import Path
import soundfile as sf, scipy.signal as ss, numpy as np, sys
root=Path(__file__).resolve().parents[1]
media=Path(sys.argv[1])
for model,source,file,kind,rate,times in [
    ('htdemucs_ft','farebi','Farebi - drum kit','drums',90/84,[8,16,27,50.67,59,67,99,139,155,161,208,216,227,231]),
    ('htdemucs_ft','farebi','Farebi - hook lead','vocals',90/84,[49.3,51,61,68,207,209,218,229]),
    ('htdemucs','namastute','Namastute - performance','vocals',80/84,[6.32,18,29,42,54,59.5,60.5,66,85,107])]:
    def env(p):
        x,sr=sf.read(p,dtype='float32')
        x=ss.sosfilt(ss.butter(2,100,fs=sr,btype='highpass',output='sos'),x,axis=0)
        n=sr//100
        return np.sqrt(np.mean(x[:len(x)//n*n].reshape(-1,n,2)**2,axis=(1,2)))
    x=env(root/'stems/demucs'/model/source/(kind+'.wav'))
    y=env(media/(file+'.wav'))
    x=np.interp(np.arange(round(len(x)*rate))/rate,np.arange(len(x)),x)
    for t in times:
        i=round(t*rate*100); off=np.arange(-12,13)
        ref=x[i-20:i+82]
        cc=[np.corrcoef(ref,y[i+z-20:i+z+82])[0,1] for z in off]
        j=int(np.argmax(cc))
        print(source,kind,t, int(off[j]*10),round(cc[j],2))
