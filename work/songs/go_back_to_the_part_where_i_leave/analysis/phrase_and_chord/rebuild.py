"""Crossfade isolated tonal parts and restore one phrase's source delivery."""
import json
from pathlib import Path
import re
import sys

from demucs.apply import apply_model
from demucs.pretrained import get_model
import numpy as np
from pedalboard import PeakFilter
from scipy import signal
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
import soundfile as sf
import torch

stage=Path(__file__).resolve().parent
root=stage.parents[4]
project=root/'reaper/Go Back to the Part Where I Leave'
media=project/'Media'
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, load

n=lambda t:round(t*SR)
g=json.loads((stage.parent/'vocal_clarity/edits.json').read_text())
j=g['kanye_bar']-120/87
start=g['last_rewind_end']
full=g['harmony_full']
origin=n(16.551088435374)
base_name='Runaway - vocal space and gradual return.wav'
em_name='Eminem - tuned lead with phrase detail.wav'
bed=load(media/base_name)
straight=load(media/'Runaway - extended handoffs.wav')
original_bed=load(media/'Runaway - continuous groove.wav')

def window(x,t,u,offset=0):
    return x[n(t)-offset:n(u)-offset]

def rms_db(x):
    return float(10*np.log10(np.mean(x*x)+1e-12))

def curve(times,points):
    x,y=np.asarray(points).T
    return PchipInterpolator(x,y)(np.clip(times,x[0],x[-1])).astype(np.float32)[:,None]

def band(x,lo,hi):
    s=signal.butter(2,[lo,hi],fs=SR,btype='bandpass',output='sos')
    return signal.sosfiltfilt(s,x,axis=0).astype(np.float32)

a,b=n(127.95),n(134.7)
times=np.arange(a,b)/SR
reference=bed[a-origin:b-origin]
outgoing=straight[a-origin:b-origin].copy()
echo_at=n(30*240/87)+n(120/87)-origin
alignment=n(j)-echo_at
incoming=original_bed[a-alignment:b-alignment].copy()
incoming=PeakFilter(cutoff_frequency_hz=1030,gain_db=1.0,q=.77)(incoming.T,SR).T
# The incoming tonal reference is the same source as the current E
# groove. Match its gain at the existing full-level point.
fit=slice(n(full+.025)-a,n(g['kanye_bar']-.055)-a)
gain=float(np.sum(reference[fit]*incoming[fit])/np.sum(incoming[fit]**2))
assert .4<gain<2 and np.corrcoef(reference[fit].ravel(),incoming[fit].ravel())[0,1]>.96
incoming*=gain
# Extend the outgoing D-sharp harmony with the preceding bar's source.
loop=n(240/87)
edge=n(j-.14)
continuation=straight[edge-origin-loop:b-origin-loop]
old=outgoing[edge-a:].copy()
w=curve(times[edge-a:],[(j-.14,0),(j-.068,1),(times[-1],1)])
outgoing[edge-a:]=old+(continuation-old)*w

def separate(inputs):
    model=get_model('htdemucs').eval()
    target='mps' if torch.backends.mps.is_available() else 'cpu'
    torch.set_num_threads(5)
    with torch.inference_mode():
        batch=torch.from_numpy(np.stack(inputs).transpose(0,2,1).copy())
        try:
            estimates=apply_model(model,batch,shifts=0,split=False,device=target)
        except (NotImplementedError,RuntimeError):
            estimates=apply_model(model,batch,shifts=0,split=False,device='cpu')
    return estimates.cpu().numpy().transpose(0,1,3,2)

def get_parts():
    cache=stage/'Tonal separation.npz'
    if cache.exists():
        with np.load(cache) as f:
            return f['stems']
    stems=separate([reference,outgoing,incoming])
    np.savez(cache,stems=stems)
    return stems

stems=get_parts()
assert stems.shape==(3,4,b-a,2)
# Blend the real outgoing and incoming pitched layers directly. Both
# alternatives are in bar phase. The current drum stem and residual
# stay in place, and the bass is given a slightly later, shorter ramp.
harmony=curve(times,[(start,0),(start+.24,.12),(start+.62,.33),
                    (j,.56),(j+.50,.85),(full,1)])
bass=curve(times,[(start,0),(130.72,0),(130.99,.12),(131.28,.51),
                  (131.61,.93),(131.82,1),(full,1)])
def blend_parts(left,right,amount):
    result=left+(right-left)*amount
    # Smooth the power lost when the two source waveforms cancel in the
    # overlap. This control changes the pitched layers alone.
    hop=n(.024)
    def power(y):
        y=np.pad(y,((0,-len(y)%hop),(0,0)))
        return gaussian_filter1d(np.mean(y.reshape(-1,hop,2)**2,axis=(1,2)),2.7)
    place=(np.arange(len(power(result)))+.5)*hop
    w=np.interp(place,np.arange(len(amount)),amount[:,0])
    target=(1-w)*power(left)+w*power(right)
    adjustment=np.clip(np.sqrt(target/np.maximum(power(result),1e-8)),.84,1.52)
    gain=np.interp(np.arange(len(result)),place,adjustment)
    return (result*gain[:,None]).astype(np.float32)

new_chord=blend_parts(stems[1,2],stems[2,2],harmony)
new_bass=blend_parts(stems[1,1],stems[2,1],bass)
# Ease the louder source attack on the second beat of the return.
attack=curve(times,[(start,0),(131.44,0),(131.67,.95),(131.80,1),(full,0)])
new_chord*=db(-1.70*attack)
new_bass*=db(-.65*attack)
# The three models see different context. Taper the residual correction
# at both boundaries so the surrounding render remains sample-identical.
mix=curve(times,[(start,0),(start+.11,1),(full-.085,1),(full,0)])
chord_delta=(new_chord-stems[0,2])*mix
bass_delta=(new_bass-stems[0,1])*mix
bed[a-origin:b-origin]=reference+chord_delta+bass_delta
assert np.isfinite(bed).all()

# Restore the original, pitch-preserving delivery for both words,
# with the splice confined to the quiet edges of the phrase.
em=load(media/em_name)
source=load(media/'Eminem - Love the Way You Lie lead.wav')
assert em.shape==source.shape
em_at=n(97.874467120181)
lo,hi=n(100.611),n(101.244)
cl=lo-em_at
cr=hi-em_at
t=np.arange(lo,hi)/SR
prior=em[cl:cr].copy()
natural=source[cl:cr].copy()
core=(t>=100.67)&(t<101.186)
prior_gain=np.interp(t,[100.574,100.652,100.793,100.904,101.035],
                       [1.25169927,1.15478198,1.15478198,1.09018449,1])
new_gain=np.interp(t,[100.574,100.650,101.174,101.244],
                     [1.25169927,db(.95),db(.95),1])
natural*=db(np.clip(rms_db(band((prior*prior_gain[:,None])[core],180,6200))
                    -rms_db(band((natural*new_gain[:,None])[core],180,6200)),-2.4,2.4))
w=curve(t,[(100.611,0),(100.659,1),(101.199,1),(101.244,0)])
em[cl:cr]=prior+(natural-prior)*w

new_bed='Runaway - continuous chord crossfade.wav'
new_em='Eminem - natural really is phrase.wav'
for name,x in [(new_bed,bed),(new_em,em)]:
    sf.write(stage/'Media'/name,x,SR,'FLOAT')
text=(project/f'{project.name}.rpp').read_text()
text=re.sub(r'(?<=FILE ")Media/',str(media)+'/',text)
for old,new in [(base_name,new_bed),(em_name,new_em)]:
    assert text.count(str(media/old))==1
    text=text.replace(str(media/old),str(stage/'Media'/new))
old_points=('      PT 100.652 1.15478198 0\n'
            '      PT 100.793 1.15478198 0\n'
            '      PT 100.904 1.09018449 0\n'
            '      PT 101.035 1 0\n')
new_points=(f'      PT 100.650 {db(.95):.9f} 0\n'
            f'      PT 101.174 {db(.95):.9f} 0\n'
            '      PT 101.244 1 0\n')
assert text.count(old_points)==1
text=text.replace(old_points,new_points)
(stage/'Chord and phrase edit.rpp').write_text(text)
np.savez(stage/'Blend check.npz',start_frame=a,phase=harmony,bass_phase=bass,
         chord_delta=chord_delta,bass_delta=bass_delta)
(stage/'edits.json').write_text(json.dumps({'chord':[start,full],
    'phrase':[100.574,101.244],'incoming_reference_gain':gain},indent=2)+'\n')
print('Chord',start,full,'reference gain',gain,flush=True)
