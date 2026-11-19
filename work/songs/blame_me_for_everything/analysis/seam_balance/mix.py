"""Balance the first hook exit and blend the final beat into the bridge kit."""
from math import gcd
from pathlib import Path
import json
import re
import sys

import numpy as np
from pedalboard import Reverb
from scipy.signal import butter,resample_poly,sosfiltfilt
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR,db,fade,filt

name='Blame Me for Everything.rpp'
project=root/'reaper/Blame Me for Everything'
reference=here/'Reference.rpp'
rpp=reference.read_text() if reference.exists() else (project/name).read_text()
reference.write_text(rpp)
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
media=here/'Media'
media.mkdir(exist_ok=True)
beat=60/87
n=lambda t:round(t*SR)
bridge=n(140*beat)
last_beat=bridge-n(beat)

def name_of(chunk):
    return re.search(r'(?m)^    NAME "([^"]+)"',chunk)[1]

def media_of(chunk):
    return re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]

def position(chunk):
    return n(float(re.search(r'(?m)^      POSITION (\S+)',chunk)[1]))

def load(path):
    x,rate=sf.read(path,dtype='float32',always_2d=True)
    if rate!=SR:
        d=gcd(rate,SR)
        x=resample_poly(x,SR//d,rate//d,axis=0).astype(np.float32)
    if x.shape[1]==1:
        x=np.repeat(x,2,axis=1)
    return x

def zero_phase(x,cut,kind):
    sos=butter(2,cut,fs=SR,btype=kind,output='sos')
    return sosfiltfilt(sos,x,axis=0).astype(np.float32)

def curve(t,points):
    at,values=np.array(points).T
    return np.interp(t,at,values).astype(np.float32)[:,None]

def db_rms(x):
    return float(10*np.log10(max(np.mean(x*x),1e-12)))

bed_index=next(i for i,t in enumerate(tracks) if name_of(t)=='Runaway | Instrumental')
drum_index=next(i for i,t in enumerate(tracks) if name_of(t)=='Veer | Handoff Drums')
bed_at=position(tracks[bed_index])
drum_at=position(tracks[drum_index])
bed=load(project/'Media'/media_of(tracks[bed_index]))
drums=load(project/'Media'/media_of(tracks[drum_index]))

# Balance the bass rise after the hook. The original drum transients
# and the new upright answer stay on their existing beat and tracks.
a,b=n(60.50)-bed_at,n(66.205)-bed_at
span=bed[a:b].copy()
t=(np.arange(a,b)+bed_at)/SR
low=zero_phase(span,157,'lowpass')
low_db=curve(t,[(60.50,0),(60.677,0),(60.82,-2.85),(61.5,-2.75),
                (63.45,-2.6),(64.52,-3.55),(65.18,-3.38),
                (65.68,-2.05),(66.205,0)])
trim=curve(t,[(60.50,0),(60.69,-.48),(61.4,-.68),(64.45,-.65),
              (65.55,-.52),(66.205,0)])
bed[a:b]=(span+low*(10**(low_db/20)-1))*10**(trim/20)

# Remove the isolated rim. Restore the original final beat, then
# trade the two eighth-note hat accents with the bridge kit.
i,j=last_beat-bed_at,bridge-bed_at
prior=load(project/'Media/Runaway with transition pickup.wav')
assert prior.shape==bed.shape
x=prior[i:j].copy()
top=zero_phase(x,4100,'highpass')
relative=np.arange(len(x))/SR
amount=curve(relative,[(0,0),(.10,.17),(.29,.27),(.49,.38),(beat,.36)])
bed[i:j]=x-top*amount
drums[:bridge-drum_at]=0

kit=next((root/'work/shared/composition/instruments/AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
for group in kit.read_text().split('<group>')[1:]:
    if re.search(r'\bkey=42\b',group.split('<region>',1)[0]):
        layers=re.findall(r'hivel=(\d+) sample=([^\r\n]+)',group)
        break
else:
    raise RuntimeError('Missing closed hi-hat')
hats=np.zeros((n(beat+.35),2),np.float32)
for at,velocity,target in [(0,43,-33.3),(.5,51,-30.9)]:
    sample=next(f for v,f in layers if velocity<=int(v))
    h=load(kit.parent/sample)
    p=np.max(abs(h),axis=1)
    onset=np.flatnonzero(p>p.max()*.018)[0]
    hit=h[max(0,onset-14):onset+n(.29)]
    hit=filt(filt(hit,'highpass',2650),'lowpass',13100)
    hit=fade(hit,.003,.091)
    hit*=db(target-db_rms(hit[:n(.11)]))
    a=n(at*beat)
    hats[a:a+len(hit)]+=hit
hats=Reverb(room_size=.38,damping=.68,wet_level=.15,dry_level=.94,width=.86)(hats.T,SR).T
hats=fade(hats,.009,.26)
offset=last_beat-drum_at
assert offset>=0
drums[offset:offset+len(hats)]+=hats

for index,audio,file in [(bed_index,bed,'Runaway locally balanced.wav'),
                         (drum_index,drums,'Bridge drums with hat handover.wav')]:
    sf.write(media/file,audio,SR,'FLOAT')
    tracks[index]=re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',tracks[index])
final=header+''.join(tracks)+'>\n'
(here/name).write_text(final)
names={p.name for p in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',lambda m:str((media if m[1] in names else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
report={'first_hat_seconds':round(last_beat/SR,4),'second_hat_seconds':round((last_beat+n(.5*beat))/SR,4),
        'bridge_seconds':round(bridge/SR,4),
        'native_bed_is_silent_under_bridge':bool(not np.any(bed[bridge-bed_at:n(148*beat)-bed_at]))}
(here/'edit-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
