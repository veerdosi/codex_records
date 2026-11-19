from pathlib import Path
import json
import numpy as np
import soundfile as sf
import soxr,librosa
from scipy import signal

p=Path(__file__).resolve().parent
R=json.loads((p/'render_report.json').read_text())
SR=16000
def audio(path,a,b):
    with sf.SoundFile(path) as f:
        f.seek(round(a*f.samplerate))
        return soxr.resample(f.read(round((b-a)*f.samplerate),dtype='float32').mean(1),f.samplerate,SR)
def norm(x):
    return x/(np.linalg.norm(x)+1e-9)
def label(path,t):
    for line in path.read_text().splitlines():
        a,b,c=line.split()
        if float(a)<=t<float(b):return c
    return 'N'
def rhythm(name,origin,anchor,beat,bars):
    path=p/'stems'/'htdemucs'/f'{name}_verse_instrumental'/'drums.wav'
    starts=np.array([anchor+bar*4*beat for bar in bars])
    low=starts[0]-.08
    x=audio(path,low-origin,starts[-1]+4*beat+.13-origin)
    profiles=[]
    for band in [(42,151),(410,1500),(1750,6400)]:
        y=signal.sosfilt(signal.butter(2,band,fs=SR,btype='bandpass',output='sos'),x)
        values=[]
        for start in starts:
            values.append([np.mean(y[round((start+j*beat/2-low-.018)*SR):
                                    round((start+j*beat/2-low+.075)*SR)]**2)
                           for j in range(8)])
        profiles.append(norm(np.median(values,axis=0)))
    return np.stack(profiles)

def chroma(path,a,b):
    y=audio(path,a,b)
    y=librosa.effects.harmonic(y)
    c=librosa.feature.chroma_stft(y=y,sr=SR,hop_length=256)
    return norm(c.mean(axis=1))
def metrics(a,b):
    y=audio(p/'what_it_cost_preview.wav',a,b)
    h=1600; n=len(y)//h
    v=np.mean(y[:n*h].reshape(n,h)**2,axis=1)
    cen=librosa.feature.spectral_centroid(y=y,sr=SR)
    return [round(10*np.log10(np.mean(v)+1e-10),2),
            round(float(np.median(cen)),1),
            round(float(np.percentile(10*np.log10(v+1e-10),80)-np.percentile(10*np.log10(v+1e-10),20)),2)]

k0=R['kanye_source_start'];c0=R['travis_source_bar'];beat=60/95
k=rhythm('wonder',169,k0,60/95.7,range(1,8))
print('Kanye high-band backbeat bins',np.argsort(k[2])[-2:].tolist())
for delta in [-1,0,1]:
    c=rhythm('coffee',95,c0+delta*beat,beat,range(-7,-1))
    similarity=(k*c).sum(axis=1)
    print('Coffee beat offset',delta,'kick/mid/backbeat similarity',np.round(similarity,3).tolist(),
        'strong high-band bins',np.argsort(c[2])[-2:].tolist(),
        'chord',label(p/'coffee.lab',c0+delta*beat+.12))
ka=chroma(p/'wonder_verse_instrumental.wav',191.55-169,192.85-169)
ca=chroma(p/'coffee_verse_instrumental.wav',c0-95,c0+.95-95)
print('Verse pivot labels',label(p/'wonder.lab',192.2),label(p/'coffee.lab',c0+.18))
print('Chroma overlap by semitones (-2 to +2)',[round(float(np.roll(ka,s)@ca),3) for s in range(-2,3)])
for delta in [-1,0,1]:
    t=R['string_start']+delta*4*beat
    a=c0+11*4*beat
    l0=label(p/'coffee.lab',a-.1);l1=label(p/'coffee.lab',t+.12)
    h=chroma(p/'coffee.wav',a-.68,a+.14)@chroma(p/'coffee.wav',t-.12,t+.73)
    print('String edit whole-bar offset',delta,'labels',l0,l1,'chroma',round(float(h),3))
for name,a,b in [('intro',0,2.9),('Kanye',4.2,21.5),('pivot',21.5,24.0),('Travis',25.5,47.5),
                 ('string entrance',49.7,53.3),('release',54,69)]:
    print(name,'RMS dBFS, spectral center Hz, short-term spread dB',metrics(a,b))
