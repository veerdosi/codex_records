"""Compare vocal phrasing and backing dynamics at the revised gestures."""
from pathlib import Path
import json
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.ndimage import gaussian_filter1d
import soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

here=Path(__file__).resolve().parent
old=here.parent/'shoegaze'
checks=[(40.2,42.17),(83.23,84.45),(107.55,109.28),(118.7,120.55),(142.45,145.08),
        (149.32,150.52),(157.35,160.79),(168.19,171.76)]
r=44100

def read(folder,filename):
    x,rate=sf.read(folder/(filename+'.wav'),dtype='float32')
    assert rate==r
    return x

def band(x,lo,hi):
    return sosfilt(butter(2,[lo,hi],btype='bandpass',fs=r,output='sos'),x,axis=0)

def levels(x):
    window=round(.05*r)
    e=(x[:len(x)//window*window]**2).reshape(-1,window,2).mean(axis=(1,2))
    return 10*np.log10(np.maximum(1e-12,gaussian_filter1d(e,2.1)))

def crop(x,a,b):
    return x[round(a*r):round(b*r)]

v=read(old,'Voice')
oldmix,newmix=read(old,'Premaster'),read(here,'Premaster')
oldbed,newbed=read(old,'Backing'),read(here,'Backing')
oldg,newg=read(old,'Guitars'),read(here,'Guitars')
assert all(x.shape==v.shape for x in (oldmix,newmix,oldbed,newbed,oldg,newg))
assert np.max(abs(newmix-newbed-v))<1.5e-6
assert np.isfinite(newmix).all() and np.max(np.abs(newmix))<1
delta=newmix-oldmix
t=0.
for a,b in checks+[ (len(v)/r,len(v)/r) ]:
    max_error=np.max(abs(crop(delta,t,a-.011)))
    # REAPER interpolates envelope values in render blocks.
    assert max_error<1e-5,(t,a,max_error)
    t=b+.011
fig,axes=plt.subplots(len(checks),1,figsize=(10,14),constrained_layout=True)
report=[]
for ax,(a,b) in zip(axes,checks):
    start,end=a-.8,b+.8
    f=lambda x:crop(x,start,end)
    oldclip,newclip=f(oldmix),f(newmix)
    match=np.sqrt(np.mean(oldclip**2)/np.mean(newclip**2))
    contours=[('Lead',v,300,4200,1.),('Guitar before',oldg,270,3800,1.),
              ('Guitar after, level matched',newg,270,3800,match)]
    changes=[]
    for label,stem,lo,hi,gain in contours:
        e=levels(band(f(stem),lo,hi)*gain)
        time=start+.025+np.arange(len(e))*.05
        ax.plot(time,e,label=label)
        changes.append(e)
    inside=(time>=a)&(time<=b)
    ax.axvspan(a,b,alpha=.08,color='black')
    ax.set(xlim=(start,end),ylim=(-52,-15),ylabel='dBFS')
    report.append({'start':a,'end':b,'peak_guitar_difference_db':float(np.max((changes[2]-changes[1])[inside])),
                   'lead_unchanged':True})
axes[0].legend(loc='lower left',fontsize=8)
axes[-1].set_xlabel('Song time (s)')
fig.savefig(here/'Phrasing comparison.png',dpi=115)
(here/'review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
