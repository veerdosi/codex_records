from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import numpy as np
import soundfile as sf
from scipy import signal

SR=44100

def load(path):
    y,sr=sf.read(path,dtype='float32',always_2d=True)
    if sr!=SR:
        import soxr
        y=soxr.resample(y,sr,SR)
    return y

def db(x):
    return 10**(x/20)

def filt(y,kind,freq,order=2):
    return signal.sosfilt(signal.butter(order,freq,btype=kind,fs=SR,output='sos'),y,axis=0).astype(np.float32)

def fade(y,fi=.008,fo=.025):
    y=y.copy()
    ni=min(round(fi*SR),len(y)); no=min(round(fo*SR),len(y))
    if ni:y[:ni]*=np.sin(np.linspace(0,np.pi/2,ni,dtype=np.float32))[:,None]**2
    if no:y[-no:]*=np.cos(np.linspace(0,np.pi/2,no,dtype=np.float32))[:,None]**2
    return y

def stretch(y, duration, key, *, cache_dir=None):
    cache = Path(cache_dir) / f'{key}.wav' if cache_dir is not None else None
    if cache is not None and cache.is_file():
        out = load(cache)
    else:
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix='rubberband-', dir=cache.parent if cache else None) as scratch:
            src = Path(scratch) / 'source.wav'
            dest = Path(scratch) / 'stretched.wav'
            sf.write(src, y, SR, subtype='FLOAT')
            subprocess.run(
                ['rubberband', '-3', '--centre-focus', '-D', str(duration), str(src), str(dest)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            out = load(dest)
            if cache is not None:
                dest.replace(cache)
    n = round(duration * SR)
    if len(out)<n:out=np.pad(out,((0,n-len(out)),(0,0)))
    return out[:n]

def delay(y,beat=.789473684,amount=.09,feedback=.32,lowpass=4000):
    wet=filt(y,'lowpass',lowpass)
    out=np.zeros((len(y)+round(beat*4*SR),2),dtype=np.float32)
    for tap in range(1,5):
        offset=round(beat*tap*SR)
        v=wet[:,::-1] if tap%2 else wet
        out[offset:offset+len(v)]+=v*amount*feedback**(tap-1)
    out[:len(y)]+=y
    return out

def mono_low(y,cutoff=130):
    low=filt(y,'lowpass',cutoff)
    return y-low+low.mean(axis=1,keepdims=True)

def peak_report(y):
    return {'peak_dbfs':float(20*np.log10(max(float(np.max(np.abs(y))),1e-12))),
            'rms_dbfs':float(20*np.log10(max(float(np.sqrt(np.mean(y.astype(np.float64)**2))),1e-12))),
            'finite':bool(np.isfinite(y).all()),'correlation':float(np.corrcoef(y.T)[0,1])}
