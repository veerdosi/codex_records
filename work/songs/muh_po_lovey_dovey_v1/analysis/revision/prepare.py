"""Prepare Farebi on the rap's original tempo; preserve Namastute's cadence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess as sp, sys
from tempfile import TemporaryDirectory
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
p=Path(__file__).resolve().parents[2]
media=Path(sys.argv[1])
def job(name,stem,hp):
    x,s=sf.read(p/'stems/demucs/htdemucs_ft/farebi'/f'{stem}.wav',dtype='float32')
    x=sosfilt(butter(2,hp,fs=s,btype='highpass',output='sos'),x,axis=0)
    with TemporaryDirectory() as td:
        a,b=[Path(td)/z for z in ('a.wav','b.wav')]
        sf.write(a,x,s,subtype='FLOAT')
        sp.run(['rubberband','-q','-3',*(['-F'] if stem=='vocals' else []),'-T','90:80',str(a),str(b)],check=True)
        y,s=sf.read(b,dtype='float32')
    y=resample_poly(y,160,147,axis=0)
    peak=np.max(np.abs(y))
    sf.write(media/(name+'.wav'),y*min(1,.999/peak),48000,subtype='PCM_24')
    print(name,len(y)/48000,float(peak),flush=True)
x,s=sf.read(p/'stems/demucs/htdemucs/namastute/vocals.wav',dtype='float32')
x=sosfilt(butter(2,87,fs=s,btype='highpass',output='sos'),x,axis=0)
sf.write(media/'Namastute - native vocals.wav',resample_poly(x,160,147,axis=0),48000,subtype='PCM_24')
with ThreadPoolExecutor(4) as pool:
    for fut in [pool.submit(job,*a) for a in [('Farebi - drums','drums',27),('Farebi - bass','bass',29),
                  ('Farebi - music','other',73),('Farebi - chorus','vocals',79)]]: fut.result()
