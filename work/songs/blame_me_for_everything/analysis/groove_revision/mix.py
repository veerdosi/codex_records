"""Ease into the original bridge and improve Savage's diction in the mix."""
from functools import lru_cache
from math import gcd
from pathlib import Path
import json
import re
import sys

import numpy as np
from pedalboard import HighShelfFilter, PeakFilter, Pedalboard, Reverb
from scipy.ndimage import gaussian_filter1d
from scipy.signal import resample_poly,welch
import soundfile as sf

here=Path(__file__).resolve().parent
song=here.parents[1]
root=song.parents[2]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

name='Blame Me for Everything.rpp'
project=root/'reaper/Blame Me for Everything'
reference=here/'Reference.rpp'
rpp=reference.read_text() if reference.exists() else (project/name).read_text()
reference.write_text(rpp)
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
stage=here/'Media'
stage.mkdir(exist_ok=True)
beat=60/87
bar=4*beat
n=lambda t:round(t*SR)
begin=n(35*bar)
lead_in=begin-n(beat)
end=n(37*bar)
instruments=root/'work/shared/composition/instruments'
notes=json.loads((here/'notes.json').read_text())

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def blocks(x,seconds=.08):
    step=n(seconds)
    return np.mean(x[:len(x)//step*step].reshape(-1,step,2)**2,axis=(1,2))

def loud(x):
    p=blocks(x)
    return 10*np.log10(p[p>p.max()*.075].mean())

def match(x,target):
    return x*db(target-loud(x))

def curve(x,points):
    t=np.arange(len(x))/SR
    return x*np.interp(t,*np.array(points).T).astype(np.float32)[:,None]

def read(chunk):
    get=lambda f:n(float(re.search(rf'(?m)^      {f} (\S+)',chunk)[1]))
    a,length,off=[get(f) for f in ('POSITION','LENGTH','SOFFS')]
    file=re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    with sf.SoundFile(project/'Media'/file) as f:
        f.seek(off)
        data=f.read(length,dtype='float32',always_2d=True)
    assert len(data)==length
    return a,data

def print_track(chunk,x,file,at):
    sf.write(stage/file,x,SR,'FLOAT')
    for key,val in [('POSITION',at),('LENGTH',len(x)),('SOFFS',0)]:
        chunk=re.sub(rf'(?m)^      {key} .*$',f'      {key} {val/SR:.12f}',chunk)
    return re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)

def from_samples(t):
    return (begin-lead_in)+n(t*beat)

bed_at,bed=read(tracks[3])
voice_at,old_voice=read(tracks[5])
g_at,g=read(tracks[14])
k_at,k=read(tracks[15])
b_at,old_bass=read(tracks[16])
d_at,old_drums=read(tracks[17])
assert all(x==begin for x in (g_at,k_at,b_at,d_at))
assert len(g)==len(k)==len(old_bass)==len(old_drums)
bridge_len=len(g)+begin-lead_in

# Open up the quieter consonants while keeping the top octave controlled.
voice=Pedalboard([PeakFilter(cutoff_frequency_hz=545,gain_db=-1.55,q=.88),
                 PeakFilter(cutoff_frequency_hz=2400,gain_db=.82,q=.89)])(old_voice.T,SR).T
presence=PeakFilter(cutoff_frequency_hz=3380,gain_db=2.35,q=1.00)(voice.T,SR).T
envelope=np.sqrt(gaussian_filter1d(blocks(band(voice,1900,5300),.018),1.65))
upper=np.percentile(envelope[envelope>envelope.max()*.08],83)
relative=envelope/upper
amount=np.clip((relative-.075)*6,0,1)*np.clip(1.36-.60*relative,.25,1)
w=np.interp(np.arange(len(voice)),(np.arange(len(amount))+.5)*n(.018),amount).astype(np.float32)
voice=voice+(presence-voice)*w[:,None]
target=loud(band(old_voice,190,8700))+.16
voice*=db(target-loud(band(voice,190,8700)))
voice=fade(voice,.008,.085)

# Make space in the part of the groove that overlaps the vowels and
# consonants. Keep cymbals and bass out of this dynamic dip.
a,b=voice_at-bed_at,voice_at-bed_at+len(voice)
bed_before=bed[a:b].copy()
dip=Pedalboard([PeakFilter(cutoff_frequency_hz=1780,gain_db=-1.55,q=.92),
                 PeakFilter(cutoff_frequency_hz=2930,gain_db=-.95,q=1.13)])(bed_before.T,SR).T
v=np.sqrt(gaussian_filter1d(blocks(band(voice,1150,4850),.022),2.4))
threshold=np.percentile(v[v>v.max()*.07],83)
weights=np.clip((v/threshold-.13)*1.12,0,.92)
w=np.interp(np.arange(len(voice)),(np.arange(len(weights))+.5)*n(.022),weights).astype(np.float32)
bed[a:b]=bed_before+(dip-bed_before)*w[:,None]

# Preserve the outgoing clap and hats as the new notes enter. Clear a
# little of the old sub in the final upbeat before the new A downbeat.
a,b=begin-bed_at-n(.41),begin-bed_at
outgoing=bed[a:b].copy()
sub=filt(outgoing,'lowpass',146)
bed[a:b]=outgoing-curve(sub,[(0,0),(.18,.03),(.37,.35),(.41,.49)])

def with_pickup(x):
    return np.pad(x,((begin-lead_in,0),(0,0)))

guitar,keys=with_pickup(g),with_pickup(k)
sample_root=next((instruments/'FreePats').glob('SpanishClassicalGuitar-*'))/'samples'
pickup=np.zeros((bridge_len,2),np.float32)
for at,pitch,duration,velocity in notes['Pickup guitar']:
    file={76:'E5.flac',71:'B4.flac'}[pitch]
    hit=load(sample_root/file)
    if hit.shape[1]==1:
        hit=np.repeat(hit,2,axis=1)
    strength=np.max(np.abs(hit),axis=1)
    onset=np.flatnonzero(strength>strength.max()*.011)[0]
    hit=band(hit[onset:onset+n(duration*beat+.19)],155,8900)
    hit=fade(match(hit,-29.6+(velocity-59)*.23),.012,.17)
    i=from_samples(at)
    pickup[i:i+len(hit)]+=hit
pickup=Reverb(room_size=.44,damping=.60,wet_level=.22,dry_level=.91,width=.85)(pickup.T,SR).T
guitar+=pickup
pickup=band(load(here/'Pickup keys raw.wav'),155,6600)
pickup=match(pickup,-32.5)
pickup=Reverb(room_size=.43,damping=.59,wet_level=.19,dry_level=.91,width=.87)(pickup.T,SR).T
keys[:min(len(pickup),len(keys))]+=pickup[:len(keys)]

bass=np.zeros((bridge_len,2),np.float32)
for beat_pos,pitch,duration,velocity in notes['Bass']:
    t=np.arange(n(duration*beat+.104))/SR
    f=440*2**((pitch-69)/12)
    amp=np.minimum(t/.020,1)*np.clip((len(t)/SR-t)/.10,0,1)
    x=(np.sin(2*np.pi*f*t)+.22*np.sin(4*np.pi*f*t)+.07*np.sin(6*np.pi*f*t))*amp
    x=filt(x.astype(np.float32),'lowpass',300)*(velocity/92)
    i=from_samples(beat_pos)
    bass[i:i+len(x)]+=x[:,None]
bass=match(bass,loud(old_bass)-.12)

kit=next((instruments/'AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
groups={}
for chunk in kit.read_text().split('<group>')[1:]:
    key=re.search(r'\bkey=(\d+)',chunk.split('<region>',1)[0])
    if key:
        groups[int(key[1])]=[(int(v),kit.parent/file)
            for v,file in re.findall(r'hivel=(\d+) sample=([^\r\n]+)',chunk)]

@lru_cache(maxsize=32)
def drum(pitch,velocity):
    file=next(path for upper,path in groups[pitch] if velocity<=upper)
    x,s=sf.read(file,dtype='float32',always_2d=True)
    if s!=SR:
        d=gcd(s,SR)
        x=resample_poly(x,SR//d,s//d,axis=0)
    if x.shape[1]==1:
        x=np.repeat(x,2,axis=1)
    envelope=np.max(abs(x),axis=1)
    onset=np.flatnonzero(envelope>envelope.max()*.018)[0]
    x=x[max(0,onset-16):onset+n(.33 if pitch==46 else .24)]
    return fade(x,.001,.054)*(velocity/100)*{36:1,37:.89,42:.76,46:.83}[pitch]

drums=np.zeros_like(bass)
for at,pitch,duration,velocity in notes['Drums']:
    i=from_samples(at)
    x=drum(pitch,velocity)
    drums[i:i+len(x)]+=x
drums=match(band(drums,31,14800),loud(old_drums))
# Let the existing final beat ring into Kanye as in the previous mix.
i=from_samples(7.32)
reference_drum=with_pickup(old_drums)
w=np.clip(np.arange(len(drums)-i)/n(.17),0,1).astype(np.float32)[:,None]
drums[i:]=drums[i:]*(1-w)+reference_drum[i:]*w
for x in (bass,drums):
    i=end-lead_in-n(.022)
    x[i:]=fade(x[i:],0,(len(x)-i)/SR)

changes={
 3:(bed,'Runaway with transition pickup.wav',bed_at),
 5:(voice,'Savage articulated vocal.wav',voice_at),
 14:(guitar,'Bridge nylon and pickup.wav',lead_in),
 15:(keys,'Bridge electric keys and pickup.wav',lead_in),
 16:(bass,'Bridge pocket bass.wav',lead_in),
 17:(drums,'Bridge pocket drums.wav',lead_in),
}
header=header.replace('Veer | Original guitar and keys handoff','Veer | Original bridge, Runaway pocket')
new=header+''.join(print_track(t,*changes[i]) if i in changes else t for i,t in enumerate(tracks))+'>\n'
(here/name).write_text(new)
files={p.name for p in stage.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',lambda m:str((stage if m[1] in files else project/'Media')/m[1]),new)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
def ratio(x):
    f,p=welch(x,SR,nperseg=2048,axis=0)
    return float(10*np.log10(p[(f>1800)&(f<5100)].sum()/p[(f>330)&(f<1450)].sum()))
stats={'speech_gain_db':round(float(loud(band(voice,190,8700))-loud(band(old_voice,190,8700))),2),
       'presence_vs_body_db_before':round(ratio(old_voice),2),
       'presence_vs_body_db_after':round(ratio(voice),2),
       'pickup_seconds':round(lead_in/SR,4),'bridge_seconds':round(begin/SR,4),
       'kanye_seconds':round(end/SR,4)}
(here/'mix-check.json').write_text(json.dumps(stats,indent=2)+'\n')
print(stats,flush=True)
