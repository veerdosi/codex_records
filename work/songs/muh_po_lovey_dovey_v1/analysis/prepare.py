"""Print aligned, pitch-preserving sources for the REAPER arrangement."""
from pathlib import Path
import concurrent.futures as cf
import subprocess as sp, sys
import numpy as np, soundfile as sf
from scipy import signal
from tempfile import TemporaryDirectory
p=Path(__file__).resolve().parents[1]
media=Path(sys.argv[1])
sources=p/'stems/demucs'
def stretch(name,model,song,stem,tempo,hp,lp,formant=False):
    x,s=sf.read(sources/model/song/(stem+'.wav'),dtype='float32')
    if hp: x=signal.sosfilt(signal.butter(2,hp,fs=s,btype='highpass',output='sos'),x,axis=0)
    if lp: x=signal.sosfilt(signal.butter(2,lp,fs=s,btype='lowpass',output='sos'),x,axis=0)
    with TemporaryDirectory() as td:
        a,b=[Path(td)/z for z in ('input.wav','stretch.wav')]
        sf.write(a,x,s,subtype='FLOAT')
        sp.run(['rubberband','-q','-3',*(['-F'] if formant else []),'-T',f'{tempo}:84',str(a),str(b)],check=True)
        y,s=sf.read(b,dtype='float32')
    y=signal.resample_poly(y,160,147,axis=0).astype('float32')
    sf.write(media/(name+'.wav'), y, 48000,subtype='PCM_24')
    print(name,len(y)/48000,float(np.max(np.abs(y))),flush=True)
m='htdemucs_ft'
f='farebi'
jobs=[('Farebi - drum kit',m,f,'drums',90,26,0),('Farebi - bass',m,f,'bass',90,28,0),
      ('Farebi - production',m,f,'other',90,80,0),('Farebi - hook lead',m,f,'vocals',90,87,0,True),
      ('Namastute - performance','htdemucs','namastute','vocals',80,90,0,True)]
with cf.ThreadPoolExecutor(max_workers=3) as pool:
    for future in [pool.submit(stretch,*j) for j in jobs]: future.result()
