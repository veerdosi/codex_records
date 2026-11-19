from pathlib import Path
import json
import sys
import numpy as np
import soundfile as sf
from scipy import signal
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

ROOT=Path(__file__).resolve().parent.parent
STEMS=ROOT/'stems/arrangement'
meta=json.loads((ROOT/'analysis/arrangement.json').read_text())
tracks={}
bands={}
for name in ('premaster','vocal','drums','bass','cleans','overdrive','lead','backing'):
    stereo,sr=sf.read(STEMS/(name+'.wav'),dtype='float32',always_2d=True)
    assert np.isfinite(stereo).all()
    f,t,z=signal.stft(stereo,sr,nperseg=4096,noverlap=3072,axis=0)
    power=2*np.mean(np.abs(z)**2,axis=1)/1.5
    bands[name]=np.stack([power[(f>=lo)&(f<hi)].sum(axis=0)
                          for lo,hi in ((30,125),(125,400),(400,900),(900,3600),(3600,9000),(9000,15000))])
    tracks[name]=20*np.log10(max(1e-10,np.sqrt(np.mean(stereo**2))))
    if name=='premaster':
        mix=power
        assert stereo.shape[1]==2
        print('Peak',np.max(np.abs(stereo)), 'Stereo correlation',np.corrcoef(stereo.T)[0,1],
              'Tail peak',np.max(np.abs(stereo[-int(.050*sr):])))
    del stereo,z,power

def db(x):
    return 10*np.log10(np.maximum(x,1.e-12))

summary=[]
for section in meta['sections']:
    start,stop=section['start'],section['end']
    i=(t>=start)&(t<stop)
    active=i & (db(bands['vocal'][2:4].sum(axis=0))>-42.)
    margin=db(bands['vocal'][2:4].sum(axis=0))-db(bands['backing'][2:4].sum(axis=0))
    levels={name:round(float(db(v[:,i].sum(axis=0).mean())),1)
            for name,v in bands.items() if name not in {'premaster'}}
    detail=[round(float(np.percentile(margin[active],q)),1) for q in (20,50)] if active.any() else []
    print(f"{start:5.1f}–{stop:5.1f} {section['name']:14s} {levels} lead margin {detail}")
    summary.append(dict(section,level=levels,vocal_margin=detail))
(ROOT/'analysis/mix-check.json').write_text(json.dumps(summary,indent=2))

plt.style.use('dark_background')
regions = {s['name']: (s['start'], s['end']) for s in meta['sections']}
first = regions['chorus']
last = regions['chorus2']
for region,start,stop in [('overview',0,t[-1]),('first-chorus',first[0]-6,first[1]+3),
                          ('last-chorus',last[0]-6,last[1]+5),
                          ('opening',0,20)]:
    fig,ax=plt.subplots(4,1,figsize=(13,9),sharex=True,layout='constrained')
    mask=(t>=start)&(t<=stop)
    freq=(f>=31)&(f<=15000)
    image=ax[0].pcolormesh(t[mask],f[freq],db(mix[freq][:,mask]),
                           vmin=-75,vmax=-20,shading='auto',cmap='magma')
    ax[0].set_yscale('log')
    ax[0].set_ylabel('Frequency (Hz)')
    fig.colorbar(image,ax=ax[0],label='dBFS per bin',pad=.016)
    for axis,sl,names,tag in [
        (ax[1],slice(0,2),('drums','bass','overdrive'),'30–400 Hz'),
        (ax[2],slice(2,4),('vocal','backing','cleans','overdrive','lead'),'400–3600 Hz'),
        (ax[3],slice(4,5),('drums','vocal','overdrive','cleans'),'3.6–9 kHz'),
    ]:
        for name in names:
            y=bands[name][sl].sum(axis=0)
            y=np.convolve(y,np.ones(12)/12,mode='same')
            axis.plot(t[mask],db(y[mask]),linewidth=1,label=name)
        axis.set_ylim(-70,-10)
        axis.set_ylabel(tag+'\n(dBFS)')
        axis.legend(ncols=len(names),loc='lower right')
    for section in meta['sections']:
        at=section['start']
        if start<at<stop:
            for axis in ax:
                axis.axvline(at,color='white',alpha=.25,linestyle='--')
            ax[0].text(at+.35,6500,section['name'],fontsize=7)
    ax[-1].set_xlim(start,stop)
    ax[-1].set_xlabel('Time (s)')
    fig.savefig(ROOT/'analysis'/f'{region}.png',dpi=115)
    plt.close(fig)
