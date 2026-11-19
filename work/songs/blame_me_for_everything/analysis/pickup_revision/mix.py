"""Pass the last verse accent to the bridge kit and enter on the downbeat."""
from math import gcd
from pathlib import Path
import json
import re
import sys

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt

project=root/'reaper/Blame Me for Everything'
name='Blame Me for Everything.rpp'
ref=here/'Reference.rpp'
project_text=ref.read_text() if ref.exists() else (project/name).read_text()
ref.write_text(project_text)
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',project_text)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
media=here/'Media'
media.mkdir(exist_ok=True)
n=lambda t:round(t*SR)
beat=60/87
downbeat=n(35*4*beat)
accent=downbeat-n(beat/4)

def file(chunk):
    return re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]

def position(chunk):
    return n(float(re.search(r'(?m)^      POSITION (\S+)',chunk)[1]))

def write_file(chunk,new_file,start=None,length=None):
    if start is not None:
        for key,value in [('POSITION',start),('LENGTH',length),('SOFFS',0)]:
            chunk=re.sub(rf'(?m)^      {key} .*$',f'      {key} {value/SR:.12f}',chunk)
    return re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{new_file}',chunk)

def samples(path):
    x,rate=sf.read(path,dtype='float32',always_2d=True)
    if rate!=SR:
        d=gcd(rate,SR)
        x=resample_poly(x,SR//d,rate//d,axis=0).astype(np.float32)
    if x.shape[1]==1:
        x=np.repeat(x,2,axis=1)
    return x

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def rms(x):
    return float(np.sqrt(np.mean(x*x)))

# The older instrument prints start at the first beat and have the same
# arrangement. Their files omit the extra notes before the downbeat.
for index,source in [(14,'Handoff Nylon guitar.wav'),(15,'Handoff Electric keys.wav')]:
    length=sf.info(project/'Media'/source).frames
    assert sf.info(project/'Media'/source).samplerate==SR
    tracks[index]=write_file(tracks[index],source,downbeat,length)

bed_start=position(tracks[3])
bed=samples(project/'Media'/file(tracks[3]))
d_start=position(tracks[17])
drums=samples(project/'Media'/file(tracks[17]))
drums[:downbeat-d_start]=0

# The new rim shares the existing sixteenth-note accent. Ease the
# outgoing drum mids down through that accent so the two strikes read
# as one event while the recorded bass and top end carry to the bar.
local=accent-bed_start
a,b=local-n(.014),local+n(.118)
native=bed[a:b].copy()
window=fade(np.ones_like(native),.023,.078)
bed[a:b]-=band(native,620,5400)*window*.28
kit=next((root/'work/shared/composition/instruments/AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
for group in kit.read_text().split('<group>')[1:]:
    if re.search(r'\bkey=37\b',group.split('<region>',1)[0]):
        layers=re.findall(r'hivel=(\d+) sample=([^\r\n]+)',group)
        rim_name=next(name for v,name in layers if int(v)>=62)
        break
else:
    raise RuntimeError('Missing rim articulation in the drum kit')
rim=samples(kit.parent/rim_name)
loud=np.max(abs(rim),axis=1)
onset=np.flatnonzero(loud>loud.max()*.018)[0]
rim=fade(band(rim[max(0,onset-12):onset+n(.142)],670,8450),.001,.074)
rim*=db(-7.5)*rms(band(native,620,5400))/rms(band(rim,620,5400))
j=accent-d_start
assert j+len(rim)<downbeat-d_start
drums[j:j+len(rim)]+=rim
for index,x,path in [(3,bed,'Runaway matched rim transition.wav'),(17,drums,'Bridge drums with rim pickup.wav')]:
    sf.write(media/path,x,SR,'FLOAT')
    tracks[index]=write_file(tracks[index],path)
final=header+''.join(tracks)+'>\n'
(here/name).write_text(final)
new={p.name for p in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',lambda m:str((media if m[1] in new else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
check={'rim_seconds':round(accent/SR,4),'downbeat_seconds':round(downbeat/SR,4),
       'rim_ends_before_downbeat_ms':round((downbeat-accent-len(rim))*1000/SR,1)}
(here/'timing.json').write_text(json.dumps(check,indent=2)+'\n')
print(check,flush=True)
