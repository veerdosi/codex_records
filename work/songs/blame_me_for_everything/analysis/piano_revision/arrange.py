"""Reprise the opening piano at the end and reconnect the verses on the native groove."""
from fractions import Fraction
from pathlib import Path
import json
import re
import sys

import numpy as np
from pedalboard import Reverb
from scipy.signal import correlate, correlation_lags, resample_poly
import soundfile as sf

here = Path(__file__).resolve().parent
song = here.parents[1]
root = song.parents[2]
sys.path.insert(0, str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

title = 'Blame Me for Everything'
project = root/'reaper'/title
if not project.exists():
    project = root/'reaper/When You Leave'
reference = here/'Reference.rpp'
rpp = reference.read_text() if reference.exists() else (project/'When You Leave.rpp').read_text()
reference.write_text(rpp)
header,*chunks = re.split(r'(?m)(?=^  <TRACK )',rpp)
chunks[-1] = chunks[-1].rstrip().removesuffix('>').rstrip()+'\n'
media = here/'Media'
media.mkdir(exist_ok=True)
beat,bar = 60/87,240/87

def n(t):
    return round(t*SR)

total = n(float(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)',header)[1]))

def bus():
    return np.zeros((total,2),np.float32)

def add(x,part,at):
    offset = n(at)
    stop = min(total,offset+len(part))
    x[offset:stop] += part[:stop-offset]

def clip(x,a,b):
    return x[n(a):n(b)].copy()

def read(chunk):
    get=lambda f:n(float(re.search(rf'(?m)^      {f} (\S+)',chunk)[1]))
    at,length,offset = (get(k) for k in ('POSITION','LENGTH','SOFFS'))
    file = re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    with sf.SoundFile(project/'Media'/file) as f:
        f.seek(offset)
        x = f.read(length,dtype='float32',always_2d=True)
    result = bus()
    result[at:at+len(x)] = x
    return result

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def rms(x):
    return float(np.sqrt(np.mean(x*x)))

def active_db(x):
    step=n(.12)
    p=np.mean(x[:len(x)//step*step].reshape(-1,step,2)**2,axis=(1,2))
    return float(10*np.log10(p[p>p.max()*.08].mean()))

def level(x,target):
    return x*db(target-active_db(x))

def automate(x,points):
    a,b=n(points[0][0]),min(total,n(points[-1][0]))
    at,gain=np.array(points).T
    x[a:b]*=np.interp(np.arange(a,b)/SR,at,gain).astype(np.float32)[:,None]

def read_runaway(at,duration):
    with sf.SoundFile(song/'sources/runaway.wav') as f:
        assert f.samplerate==SR
        f.seek(n(at))
        return f.read(n(duration),dtype='float32',always_2d=True)

def replace(chunk,x,file,name=None):
    active=np.flatnonzero(np.max(abs(x),axis=1)>1e-7)
    a,b=max(0,int(active[0])-32),min(len(x),int(active[-1])+33)
    sf.write(media/file,x[a:b],SR,'FLOAT')
    for field,value in [('POSITION',a/SR),('LENGTH',(b-a)/SR),('SOFFS',0)]:
        chunk=re.sub(rf'(?m)^      {field} .*$',f'      {field} {value:.12f}',chunk)
    if name:
        chunk=re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m:m[1]+f'"{name}"',chunk)
    return re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)

# Use the original E6 strike as the recognizable upper voice. Replay it
# on the same pulse, with new pitches at the ends of the phrases.
strike=fade(band(read_runaway(.087,1.12),340,9200),.003,.14)
high=bus()
for name,notes in json.loads((here/'motif.json').read_text()).items():
    for measure,offset,pitch,velocity in notes:
        ratio=Fraction(2**((88-pitch)/12)).limit_denominator(140)
        shot=resample_poly(strike,ratio.numerator,ratio.denominator,axis=0).astype(np.float32)
        shot=fade(shot[:n(1.34 if measure<71 else 1.75)],.003,.19)
        gain=-23.3+(velocity-78)*.215
        add(high,level(shot,gain),(measure*4+offset)*beat)

# The same upright, voicings, and answering melody play at both ends.
upright=bus()
for name,at,target in [('Opening',0,-25.2),('Closing',63*bar,-22.8)]:
    take=band(load(here/f'{name} upright raw.wav'),45,9000)
    take=level(take,target)
    if name=='Closing':
        automate(take,[(0,.46),(bar-.16,.58),(bar+.23,.90),(2*bar,1),
                       (7*bar,1),(8.8*bar,.93)])
    add(upright,fade(take,.022,.55 if name=='Closing' else .27),at)
for x,wet in ((high,.115),(upright,.17)):
    room=Reverb(room_size=.49,damping=.61,wet_level=wet,dry_level=.93,width=.85)
    x[:]=room(x.T,SR).T
    automate(x,[(0,.67),(2*bar,.68),(3.50*bar,.73),(5.45*bar,.88),(6.55*bar,.92)])
    automate(x,[(63*bar,.95),(64*bar-.02,.93),(64.85*bar,.76),(65.8*bar,.67),
                (67*bar,.62),(70*bar,.60),(total/SR,.54)])
    x[-n(.30):]=fade(x[-n(.30):],0,.30)

intro=read(chunks[2])
automate(intro,[(0,0),(3*bar,0),(3.42*bar,.25),(4.02*bar,.71),
                (5.22*bar,.86),(5.92*bar,.96),(6*bar,1)])
# Remove the stacked turnaround. The last complete line remains over
# C-sharp minor, then one actual Runaway A bar leads into the E downbeat.
bed=read(chunks[3])
bed_ref=bed.copy()
a,b=35*bar,36*bar
old_source=load(song/'stems/runaway_bed_source_instrumental.wav')
native_a=clip(old_source,255.96-214,255.96-214+bar)
native_a=level(native_a,active_db(clip(bed_ref,a-bar,a)))
blend=n(.035)
i,j=n(a),n(b)
native_a=native_a[:j-i]
assert len(native_a)==j-i
bed[i:j]=native_a
bed[i:i+blend]=fade(bed_ref[i:i+blend],0,.035)+fade(bed[i:i+blend],.035,0)

# Reconstruct the native Kanye backing with the original separated lead.
# This removes the earlier overlap of two drum recordings on this downbeat.
raw_begin=104.24
duration=1.55
raw=read_runaway(raw_begin,duration)
lead_source=load(here.parent/'rebuild/runaway lead.wav')
lead_source=clip(lead_source,raw_begin-103,raw_begin-103+duration)
clean=raw-band(lead_source[:len(raw)],74,12000)
offset=n(.40)
x=clean[offset:n(1.26)].mean(1)
y=bed_ref[j+offset:j+n(1.26)].mean(1)
z=correlate(x,y,method='fft')
lags=correlation_lags(len(x),len(y))
valid=abs(lags)<400
lag=int(lags[valid][np.argmax(z[valid])])
if lag!=0:
    clean=np.pad(clean,((max(0,-lag),max(0,lag)),(0,0)))
    clean=clean[max(0,lag):max(0,lag)+len(raw)]
x=clean[offset:n(1.26)].mean(1)
gain=float((x@y)/(x@x))
corr=float(np.corrcoef(x,y)[0,1])
assert .15<gain<2 and corr>.94,(gain,corr,lag)
clean*=gain
length=n(.47)
switch=n(.20)
bed[j:j+length]=clean[:length]
bed[j:j+blend]=fade(bed[j:j+blend],.035,0)+fade(
    np.repeat(bed[j-1:j],blend,axis=0),0,.011)
bed[j+length-switch:j+length]=fade(bed[j+length-switch:j+length],0,switch/SR)+fade(
    bed_ref[j+length-switch:j+length],switch/SR,0)

changes={
    0:(high,'Piano pulse.wav','Runaway piano | Opening and closing pulse'),
    1:(upright,'Piano response.wav','Veer | Answering upright'),
    2:(intro,'Piano opening drum reveal.wav',None),
    3:(bed,'Runaway native handoff.wav',None)
}
for index in (6,7,8,9,11,12,13,14):
    x=read(chunks[index])
    automate(x,[(a-.54,1),(a-.10,0),(b+.52,0),(b+1.25,1)])
    if index in (11,12):
        automate(x,[(0,0),(6*bar-.17,0),(6*bar+.85,1)])
    if index in (7,8,9,11,12,14):
        automate(x,[(63*bar+.25,1),(64*bar-.07,.38),(64.70*bar,0),(total/SR,0)])
    changes[index]=(x,f'Piano revision layer {index}.wav',None)

header=header.replace('When You Leave',title)
header=header.replace('Low piano opening','Runaway pulse and piano answer')
header=re.sub(r'(?m)^(  MARKER 2 )\S+ "Runaway piano reveal"',
              lambda m:f'{m[1]}{4*bar:.10f} "Runaway groove enters"',header)
header=header.replace('Piano turnaround','Runaway | Native A-to-E turnaround')
header=header.replace('Veer | Original piano outro','Piano motif reprise')
pieces=[]
for i,chunk in enumerate(chunks):
    if i!=10:
        pieces.append(replace(chunk,*changes[i]) if i in changes else chunk)
final=header+''.join(pieces)+'>\n'
(here/f'{title}.rpp').write_text(final)
files={x.name for x in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((media if m[1] in files else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
premaster=sum(changes[i][0] if i in changes else read(chunk)
              for i,chunk in enumerate(chunks) if i!=10)
sf.write(here/'Premaster.wav',premaster,SR,'FLOAT')
print('Native Kanye backing aligned',round(corr,4),lag,'samples',flush=True)
for t in [4*bar,6*bar,35*bar,36*bar,63*bar,64*bar,65*bar,67*bar]:
    print(round(t,3),'backing -1/+1 beat',
          [round(20*np.log10(rms(clip(premaster,t+k*beat,t+(k+1)*beat))),1) for k in (-1,0)],flush=True)
