"""Clear the two leads and let the E harmony emerge after the final rewind."""
import json
from pathlib import Path
import re
import sys

import librosa
import numpy as np
from pedalboard import HighShelfFilter, PeakFilter
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
project = root/'reaper/Go Back to the Part Where I Leave'
media = project/'Media'
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, load, stretch

n = lambda t: round(t*SR)
bed_at, sav_at, em_at = map(n, (16.551088435374,65.444013605442,97.874467120181))
bed_name = 'Runaway - softened harmony return.wav'
sav_name = '21 Savage - tuned lead.wav'
em_name = 'Eminem - tuned lead.wav'
bed, sav, em = [load(media/name) for name in (bed_name,sav_name,em_name)]

def band(x,lo,hi):
    sos=signal.butter(2,[lo,hi],fs=SR,btype='bandpass',output='sos')
    return signal.sosfiltfilt(sos,x,axis=0).astype(np.float32)

def bell(x,hz,gain,q):
    return PeakFilter(cutoff_frequency_hz=hz,gain_db=gain,q=q)(x.T,SR).T

def shelf(x,hz,gain):
    return HighShelfFilter(cutoff_frequency_hz=hz,gain_db=gain,q=.7)(x.T,SR).T

def smoother(seconds,points):
    times, values=np.asarray(points).T
    index=np.clip(np.searchsorted(times,seconds,side='right')-1,0,len(times)-2)
    fraction=np.clip((seconds-times[index])/(times[index+1]-times[index]),0,1)
    step=.5-.5*np.cos(np.pi*fraction)
    return (values[index]+(values[index+1]-values[index])*step).astype(np.float32)[:,None]

def rms_db(x):
    return float(10*np.log10(np.mean(x*x)+1e-12))

def local_frames(start,stop,origin):
    return slice(n(start)-origin,n(stop)-origin)

def centre_eq(x,filters):
    mid=x.mean(1,keepdims=True)
    revised=mid.copy()
    for hz,gain,q in filters:
        revised=bell(revised,hz,gain,q)
    return revised-mid

sav_start,sav_stop=65.775759637188,93.75
lo,hi=local_frames(sav_start,sav_stop,sav_at).start,local_frames(sav_start,sav_stop,sav_at).stop
voice=sav[lo:hi]
t=np.arange(len(voice))/SR
edges=smoother(t,[(0,0),(.035,1),(93.48-sav_start,1),(sav_stop-sav_start,0)])
treated=bell(voice,350,-1.28,.85)
treated=bell(treated,1530,1.35,.95)
treated=bell(treated,3550,1.82,1.06)
treated=shelf(treated,5000,1.50)
gain=min(0.0,.22-rms_db(band(treated,180,6200))+rms_db(band(voice,180,6200)))
sav[lo:hi]+=(treated*db(gain)-voice)*edges
# Make space when diction and the backing coincide. Only the middle of
# Runaway is touched; its low end and stereo sides stay independent.
h=n(.018)
artic=band(voice,820,5700)
pad=np.pad(artic,((0,-len(artic)%h),(0,0)))
power=np.sqrt(gaussian_filter1d(np.mean(pad.reshape(-1,h,2)**2,axis=(1,2)),2.1))
weight=np.clip((power/max(1e-8,np.percentile(power,65))-.19)*.92,0,1)
weight=np.interp(np.arange(len(voice)),(np.arange(len(weight))+.5)*h,weight).astype(np.float32)[:,None]*edges
part=bed[local_frames(sav_start,sav_stop,bed_at)]
part+=centre_eq(part,[(1360,-2.0,1.02),(3700,-1.45,.96),(5850,-.85,1.10)])*weight

em_start,em_stop=100.176,101.244
voice_frames=local_frames(em_start,em_stop,em_at)
original=em[voice_frames].copy()
voice=shelf(bell(bell(original,1380,1.10,1.0),3150,1.75,1.0),5100,.52)
t=np.arange(len(voice))/SR+em_start
edge=smoother(t,[(em_start,0),(100.245,1),(101.142,1),(em_stop,0)])
support=smoother(t,[(em_start,0),(100.52,0),(100.68,.75),(100.88,.75),(101.17,0),(em_stop,0)])
em[voice_frames]=original+(voice*np.power(10.,support/20)-original)*edge
part=bed[local_frames(em_start,em_stop,bed_at)]
space=smoother(t,[(em_start,0),(100.254,.90),(100.42,.96),(100.59,1),(100.79,.83),(101.10,.73),(em_stop,0)])
part+=centre_eq(part,[(1410,-2.5,1.0),(3530,-2.4,1.02),(5650,-1.45,1.0)])*space

# Add an earlier harmonic-only anticipation. It hands over to the
# existing printed fade and is gone at the original full-chord point.
grid=json.loads((stage.parent/'pickup_cleanup/spaced_grid.json').read_text())
old=json.loads((stage.parent/'transition_remaster/revision.json').read_text())
join,downbeat=grid['gaps'][1]
rewind_offset=grid['eminem_bar']-old['eminem_bar']
rewind_end=old['rewind_beats'][-1]+rewind_offset+(53.64-53.17)
full=join+.94
unchanged=load(media/'Runaway - extended handoffs.wav')
seed=unchanged[local_frames(join+.09,downbeat,bed_at)]
harmonics=[]
for channel in seed.T:
    spec=librosa.stft(channel,n_fft=2048,hop_length=256)
    harmonic,_=librosa.decompose.hpss(spec,kernel_size=(23,17),margin=(2.5,1.0))
    harmonics.append(librosa.istft(harmonic,hop_length=256,length=len(channel)))
harmonic=band(np.column_stack(harmonics),250,4100)
extension=stretch(harmonic,(n(full)-n(rewind_end))/SR,'harmony fade')
extension*=db(rms_db(band(seed,250,4100))-rms_db(extension)-1.65)
t=np.arange(len(extension))/SR+rewind_end
old_weight=np.interp(t, [rewind_end,join+.035,join+.26,join+.58,full],[0,0,.22,.62,1])[:,None]
wanted=smoother(t,[(rewind_end,0),(130.46,.058),(130.78,.162),(join,.27),
                    (join+.30,.50),(join+.61,.76),(full,1)])
makeup=np.maximum(wanted-old_weight,0)
last=smoother(t,[(rewind_end,1),(full-.085,1),(full,0)])
bed[local_frames(rewind_end,full,bed_at)]+=extension*makeup*last

replacements = {
    bed_name: ('Runaway - vocal space and gradual return.wav',bed),
    sav_name: ('21 Savage - tuned lead with clearer diction.wav',sav),
    em_name: ('Eminem - tuned lead with phrase detail.wav',em),
}
text=(project/f'{project.name}.rpp').read_text()
text=re.sub(r'(?<=FILE ")Media/',str(media)+'/',text)
for previous,(name,x) in replacements.items():
    assert np.isfinite(x).all()
    path=stage/'Media'/name
    sf.write(path,x,SR,'FLOAT')
    old_path=str(media/previous)
    assert text.count(old_path)==1
    text=text.replace(old_path,str(path))
(stage/'Refined vocals.rpp').write_text(text)
report={'savage':[sav_start,sav_stop],'eminem':[em_start,em_stop],
        'last_rewind_end':rewind_end,'harmony_full':full,'kanye_bar':downbeat}
(stage/'edits.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
