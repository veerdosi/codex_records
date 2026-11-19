"""Check stem balance, voiced correction, and the three on-grid rewinds."""
import json
from pathlib import Path
import re

import numpy as np
from scipy import signal
import soundfile as sf

from tune import KEY, pitch

stage=Path(__file__).resolve().parent
root=stage.parents[4]
project=root/'reaper/Go Back to the Part Where I Leave'
info=json.loads((stage/'revision.json').read_text())
RATE=44100
bar=240/87
beat=bar/4


def level(x):
    return float(10*np.log10(np.mean(x*x)+1e-12))


def band(x, limits):
    return signal.sosfilt(signal.butter(3,limits,btype='bandpass',fs=RATE,output='sos'),x,axis=0)


def read(path):
    x, rate=sf.read(path,dtype='float32',always_2d=True)
    assert rate==RATE and np.isfinite(x).all(),path
    return x


def window(x,a,b,start=55):
    return x[round((a-start)*RATE):round((b-start)*RATE)]


comparison={}
windows=[('outgoing hook',55,60.2,0),('Savage pickup',62.4,65.4,0),('Savage verse',66.25,93.45,0),
         ('Eminem verse',98.1,126.6,bar),('Kanye verse',130.1,138.8,bar)]
for name in ['Before backing','After backing']:
    x=read(stage/(name+'.wav'))
    assert np.max(abs(x))>.25
    buffers=[x,band(x,[45,160]),band(x,[400,2500]),band(x,[2500,9000])]
    table={}
    for label,a,b,d in windows:
        if name.startswith('Before'):
            a+=d
            b+=d
        table[label]={k:round(level(window(y,a,b)),2) for k,y in zip(
            ('rms_dbfs','bass_dbfs','midrange_dbfs','presence_dbfs'),buffers)}
    comparison[name]=table

before,after=(comparison[k] for k in ('Before backing','After backing'))
for verse in ('Savage verse','Eminem verse'):
    assert after[verse]['midrange_dbfs']>before[verse]['midrange_dbfs']+1
    assert abs(after[verse]['rms_dbfs']-after['Kanye verse']['rms_dbfs'])<1.3

notes_in_key=np.array([i for i in range(34,68) if i%12 in KEY])
tuning={}
for artist,old,new in [('savage','21 Savage - Said N Done lead.wav','21 Savage - tuned lead.wav'),
                       ('eminem','Eminem - Love the Way You Lie lead.wav','Eminem - tuned lead.wav')]:
    x=read(project/'Media'/old)
    y=read(stage/'Media'/new)
    assert x.shape==y.shape
    a,b,t=pitch(x)
    c,d,_=pitch(y)
    notes=69+12*np.log2(a/440)
    result=69+12*np.log2(c/440)
    before=abs(notes[:,None]-notes_in_key).min(1)
    after=abs(result[:,None]-notes_in_key).min(1)
    m=np.loadtxt(stage/f'{artist}_pitchmap.txt')
    wanted=np.interp(t,m[:,0]/RATE,m[:,1])
    valid=(abs(wanted)>.11)&np.isfinite(after)&np.isfinite(before)&(abs(result-notes)<1.2)&(b>.60)&(d>.60)
    direction=np.corrcoef((result-notes)[valid],wanted[valid])[0,1]
    assert valid.sum()>200 and direction>.55 and after[valid].mean()<before[valid].mean()
    tuning[artist]={'voiced_frames':int(valid.sum()),'target_tracking':round(float(direction),3),
                    'deviation_from_key_cents_before':round(100*float(before[valid].mean()),2),
                    'deviation_from_key_cents_after':round(100*float(after[valid].mean()),2),
                    'sample_count':len(y)}

for t in info['rewind_beats']:
    assert abs(t/beat-round(t/beat))*beat<1/RATE
assert abs(info['kanye_return']/bar-round(info['kanye_return']/bar))*bar<1/RATE
pre=read(stage/'Premaster.wav')
assert abs(len(pre)/RATE-info['duration'])<.025
assert np.max(abs(pre))>.35
assert all(level(window(pre,a,b,start=0))>-30 for a,b in [
    (10,15),(62,65),(66,92),(94,97),(99,126),(126.8,130),(134,167),(190,202)])
s={'backing':comparison,'pitch':tuning,'rewind_beats':info['rewind_beats'],'kanye_downbeat':info['kanye_return']}
(stage/'verification.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(s,indent=2))
