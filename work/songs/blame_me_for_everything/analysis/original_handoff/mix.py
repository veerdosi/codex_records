"""Mix a new two-bar handoff, recover vocal presence, and stage REAPER."""
from functools import lru_cache
from math import gcd
from pathlib import Path
from uuid import uuid4
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

project=root/'reaper/Blame Me for Everything'
reference=here/'Reference.rpp'
name='Blame Me for Everything.rpp'
rpp=reference.read_text() if reference.exists() else (project/name).read_text()
reference.write_text(rpp)
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
stage=here/'Media'
stage.mkdir(exist_ok=True)
beat=60/87
bar=4*beat
n=lambda t:round(t*SR)
start,end=n(35*bar),n(37*bar)
bridge_len=end-start
sound_len=bridge_len+n(.55)
instruments=root/'work/shared/composition/instruments'

def guid():
    return '{'+str(uuid4()).upper()+'}'

def band(x,a,b):
    return filt(filt(x,'highpass',a),'lowpass',b)

def power(x,seconds=.12):
    k=n(seconds)
    return np.mean(x[:len(x)//k*k].reshape(-1,k,2)**2,axis=(1,2))

def active_db(x):
    p=power(x)
    return 10*np.log10(p[p>p.max()*.07].mean())

def match(x,target):
    return x*db(target-active_db(x))

def pad(x,length):
    return np.pad(x,((0,max(0,length-len(x))),(0,0)))[:length]

def read(chunk):
    fields={k:n(float(re.search(rf'(?m)^      {k} (\S+)',chunk)[1]))
            for k in ('POSITION','LENGTH','SOFFS')}
    file=re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    with sf.SoundFile(project/'Media'/file) as f:
        f.seek(fields['SOFFS'])
        audio=f.read(fields['LENGTH'],dtype='float32',always_2d=True)
    assert len(audio)==fields['LENGTH']
    return fields['POSITION'],audio

def print_track(chunk,audio,file,position,label=None):
    sf.write(stage/file,audio,SR,'FLOAT')
    for key,value in [('POSITION',position),('LENGTH',len(audio)),('SOFFS',0)]:
        chunk=re.sub(rf'(?m)^      {key} .*$',f'      {key} {value/SR:.12f}',chunk)
    if label:
        chunk=re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m:m[1]+f'"{label}"',chunk)
    return re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)

def part_track(audio,label,file,iid):
    track=tracks[-1]
    track=re.sub(r'\{[0-9A-F-]{36}\}',lambda _:guid(),track)
    track=re.sub(r'(?m)^      IID .*$',f'      IID {iid}',track)
    return print_track(track,audio,file,start,label)

bed_at,bed=read(tracks[3])
voice_at,old_vocal=read(tracks[5])
clarity=here.parent/'clarity_revision'
dry=pad(load(clarity/'Fresh aligned.wav'),len(old_vocal))
tuned=pad(load(clarity/'Fresh tuned.wav'),len(old_vocal))
pm=np.loadtxt(clarity/'pitch-map.txt')
pitch_envelope=np.interp(np.arange(len(dry)),pm[:,0],
                        np.clip(abs(pm[:,1])*8,0,.88)).astype(np.float32)[:,None]
voice=dry+pitch_envelope*(tuned-dry)
mid=voice.mean(axis=1,keepdims=True)
voice=mid+(voice-mid)*.78
eq=Pedalboard([PeakFilter(cutoff_frequency_hz=345,gain_db=-2.4,q=.83),
               PeakFilter(cutoff_frequency_hz=610,gain_db=-1.3,q=1.04),
               PeakFilter(cutoff_frequency_hz=2500,gain_db=1.45,q=.95),
               PeakFilter(cutoff_frequency_hz=4420,gain_db=3.1,q=.84),
               HighShelfFilter(cutoff_frequency_hz=6900,gain_db=2.55,q=.72),
               Reverb(room_size=.36,damping=.61,wet_level=.029,dry_level=.96,width=.82)])
voice=eq(voice.T,SR).T
# Control only the very brightest syllable peaks after the presence lift.
h=filt(voice,'highpass',6550)
step=n(.018)
p=power(h,.018)
env=np.sqrt(gaussian_filter1d(p,1.7))
limit=np.percentile(env[env>env.max()*.055],94)
reduction=np.clip(1-limit/np.maximum(env,1e-8),0,.16)
voice-=h*np.interp(np.arange(len(voice)),(np.arange(len(env))+.5)*step,reduction).astype(np.float32)[:,None]
voice*=db(active_db(band(old_vocal,190,8700))-active_db(band(voice,190,8700))-.08)
voice=fade(voice,.009,.094)

# Give consonants room in the backing only while they are present.
lo=voice_at-bed_at
hi=lo+len(voice)
old_bed=bed[lo:hi].copy()
mask=PeakFilter(cutoff_frequency_hz=3460,gain_db=-2.4,q=.96)(old_bed.T,SR).T
v=band(voice,1850,4950)
step=n(.022)
p=power(v,.022)
env=np.sqrt(gaussian_filter1d(p,2.2))
ceiling=np.percentile(env[env>env.max()*.07],88)
amount=np.clip((env/ceiling-.16)*1.12,0,.95)
weights=np.interp(np.arange(len(voice)),(np.arange(len(env))+.5)*step,amount).astype(np.float32)[:,None]
bed[lo:hi]=old_bed+(mask-old_bed)*weights

# The complete bridge is our own performance. The sample below is only
# used as the outgoing and incoming arrangement outside that interval.
a,b=start-bed_at,end-bed_at
edge=n(.04)
bed[a-edge:a]=fade(bed[a-edge:a],0,.04)
bed[a:b]=0
bed[b:b+n(.012)]=fade(bed[b:b+n(.012)],.012,0)
entry=bed[b:b+n(.93)].copy()
soft_entry=Pedalboard([PeakFilter(cutoff_frequency_hz=1770,gain_db=-1.4,q=.72),
                       HighShelfFilter(cutoff_frequency_hz=5400,gain_db=-1.8,q=.76)])(entry.T,SR).T
entry_time=np.arange(len(entry))/SR
bed[b:b+len(entry)]=entry+(soft_entry-entry)*np.interp(
    entry_time,[0,.16,.93],[1,.84,0]).astype(np.float32)[:,None]

notes=json.loads((here/'notes.json').read_text())
guitar=band(pad(load(here/'Guitar raw.wav'),sound_len),145,9100)
guitar=Pedalboard([PeakFilter(cutoff_frequency_hz=470,gain_db=-2.8,q=.91),
                  HighShelfFilter(cutoff_frequency_hz=1700,gain_db=4.6,q=.72)])(guitar.T,SR).T
guitar=Reverb(room_size=.48,damping=.59,wet_level=.25,dry_level=.87,width=.92)(guitar.T,SR).T
guitar=match(guitar,-24.0)
echo=n(.75*beat)
tail=band(guitar.copy(),440,3100)
guitar[echo:]+=tail[:-echo,::-1]*db(-17.4)
keys=band(pad(load(here/'Keys raw.wav'),sound_len),135,7000)
keys=Reverb(room_size=.52,damping=.57,wet_level=.22,dry_level=.87,width=.86)(keys.T,SR).T
keys=match(keys,-27.2)
# Short FM tines double four of the picked notes. The upper partials
# keep the second bar open as the instruments hand back to Runaway.
for position,pitch,level in [(3.59,76,-30.4),(4.51,78,-27.7),(6.34,71,-29.0),
                             (7.43,75,-27.3),(7.87,76,-29.1)]:
    t=np.arange(n(.61))/SR
    w=2*np.pi*440*2**((pitch-69)/12)*t
    hit=(np.sin(w+(.52*np.exp(-t*9)+.11)*np.sin(2*w))+.24*np.sin(3*w))*np.exp(-t*7.2)
    hit=hit*np.minimum(t/.013,1)*np.minimum((len(t)/SR-t)/.10,1)
    hit=filt(hit.astype(np.float32),'highpass',890)
    hit*=db(level)/np.sqrt(np.mean(hit*hit))
    at=n(position*beat)
    length=min(len(hit),len(keys)-at)
    keys[at:at+length]+=hit[:length,None]*[.78,.59]

bass=np.zeros((sound_len,2),np.float32)
for beat_pos,pitch,length,vel in notes['Bass']:
    t=np.arange(n(length*beat+.094))/SR
    f=440*2**((pitch-69)/12)
    env=np.minimum(1,t/.022)*np.clip((len(t)/SR-t)/.10,0,1)
    x=(np.sin(2*np.pi*f*t)+.22*np.sin(4*np.pi*f*t)+.07*np.sin(6*np.pi*f*t))*env
    x=filt(x.astype(np.float32),'lowpass',300)*(vel/92)
    at=n(beat_pos*beat)
    bass[at:at+len(x)]+=x[:,None]
bass=match(bass,-21.6)

kit=next((instruments/'AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
groups={}
for group in kit.read_text().split('<group>')[1:]:
    key=re.search(r'\bkey=(\d+)',group.split('<region>',1)[0])
    if key:
        groups[int(key[1])]=[(int(top),kit.parent/path)
            for top,path in re.findall(r'hivel=(\d+) sample=([^\r\n]+)',group)]

@lru_cache(maxsize=32)
def hit(pitch,velocity):
    path=next(path for top,path in groups[pitch] if velocity<=top)
    x,s=sf.read(path,dtype='float32',always_2d=True)
    if s!=SR:
        d=gcd(s,SR)
        x=resample_poly(x,SR//d,s//d,axis=0)
    if x.shape[1]==1:
        x=np.repeat(x,2,axis=1)
    strength=np.max(abs(x),axis=1)
    onset=np.flatnonzero(strength>strength.max()*.018)[0]
    x=fade(x[max(0,onset-16):onset+n(.33 if pitch==46 else .24)],.001,.054)
    return x*(velocity/100)*{36:1,37:.89,42:.76,46:.83}[pitch]

drums=np.zeros_like(bass)
for at,pitch,length,velocity in notes['Drums']:
    x=hit(pitch,velocity)
    idx=n(at*beat)
    drums[idx:idx+len(x)]+=x
drums=match(band(drums,31,14800),-19.3)
drums[:n(.010)]=fade(drums[:n(.010)],.004,0)
for x in (guitar,keys):
    x[-n(.42):]=fade(x[-n(.42):],0,.42)
for x in (bass,drums):
    x[bridge_len-n(.016):]=fade(x[bridge_len-n(.016):],0,(len(x)-bridge_len+n(.016))/SR)

mix=guitar+keys+bass+drums
if active_db(mix[:bridge_len])<-17.6:
    gain=db(-17.6-active_db(mix[:bridge_len]))
    for x in (guitar,keys,bass,drums):
        x*=gain
    mix*=gain
sf.write(here/'Original bridge.wav',mix,SR,'FLOAT')
assert not np.any(bed[a:b])

changes={3:print_track(tracks[3],bed,'Runaway verse masking mix.wav',bed_at),
         5:print_track(tracks[5],voice,'Savage presence mix.wav',voice_at,
                       '21 Savage | Creepin, close vocal')}
header=header.replace('Runaway | Two-bar A-to-E turnaround','Veer | Original guitar and keys handoff')
rpp=header+''.join(changes[i] if i in changes else t for i,t in enumerate(tracks[:-1]))
for i,(label,x) in enumerate([('Nylon guitar',guitar),('Electric keys',keys),
                             ('Bass',bass),('Drums',drums)],90):
    rpp+=part_track(x,f'Veer | Handoff {label}',f'Handoff {label}.wav',i)
rpp+='>\n'
(here/name).write_text(rpp)
names={p.name for p in stage.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((stage if m[1] in names else project/'Media')/m[1]),rpp)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)

def spectral_ratio(x):
    f,p=welch(x,SR,nperseg=2048,axis=0)
    return 10*np.log10(p[(f>2200)&(f<5500)].sum()/p[(f>280)&(f<1550)].sum())
result={'voice_presence_vs_body_before':round(float(spectral_ratio(old_vocal)),2),
        'voice_presence_vs_body_after':round(float(spectral_ratio(voice)),2),
        'speech_level_change_db':round(float(active_db(band(voice,190,8700))-active_db(band(old_vocal,190,8700))),2),
        'bridge_start':round(start/SR,3),'bridge_end':round(end/SR,3),
        'bridge_active_rms':round(float(active_db(mix[:bridge_len])),2)}
(here/'mix-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(result,flush=True)
