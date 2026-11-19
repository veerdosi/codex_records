"""Mix the scored transitions against the continuous 87 BPM arrangement."""
from pathlib import Path
from uuid import uuid4
import json
import re
import sys

import numpy as np
from pedalboard import Reverb
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

project=root/'reaper/When You Leave'
staging=here/'Media'
staging.mkdir(exist_ok=True)
reference=here/'Reference.rpp'
rpp=(reference if reference.exists() else project/'When You Leave.rpp').read_text()
reference.write_text(rpp)
header,*chunks=re.split(r'(?m)(?=^  <TRACK )',rpp)
chunks[-1]=chunks[-1].rstrip().removesuffix('>').rstrip()+'\n'
total=round(float(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)',header)[1])*SR)
beat=60/87
bar=4*beat

def n(t):
    return round(t*SR)

def bus():
    return np.zeros((total,2),np.float32)

def read(chunk):
    get=lambda f:n(float(re.search(rf'(?m)^      {f} (\S+)',chunk)[1]))
    a,ln,off=[get(f) for f in ('POSITION','LENGTH','SOFFS')]
    fn=re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    with sf.SoundFile(project/'Media'/fn) as f:
        f.seek(off)
        x=f.read(ln,dtype='float32',always_2d=True)
    assert a+len(x)<=total
    out=bus()
    out[a:a+len(x)]=x
    return out,a

def clip(x,a,b):
    return x[n(a):n(b)].copy()

def add(dest,x,at):
    i=n(at)
    assert 0<=i<=i+len(x)<=len(dest)
    dest[i:i+len(x)]+=x

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def envelope(t,points):
    return np.interp(t,*np.asarray(points).T).astype(np.float32)

def automate(x,points):
    a,b=n(points[0][0]),n(points[-1][0])
    x[a:b]*=envelope(np.arange(a,b)/SR,points)[:,None]

def rms(x):
    return float(np.sqrt(np.mean(x*x)))

def level(x,target):
    step=4410
    p=np.mean(x[:len(x)//step*step].reshape(-1,step,2)**2,axis=(1,2))
    p=p[p>p.max()*.08]
    return x*(db(target)/np.sqrt(p.mean()))

def staged(chunk,x,name=None):
    old_name=re.search(r'(?m)^    NAME "([^"]+)"',chunk)[1]
    name=name or old_name
    file=f'Transition {staged.index:02}.wav'
    staged.index+=1
    ids=np.flatnonzero(np.max(np.abs(x),axis=1)>1e-7)
    a,b=max(0,int(ids[0])-32),min(len(x),int(ids[-1])+33)
    sf.write(staging/file,x[a:b],SR,'FLOAT')
    for field,value in [('POSITION',a/SR),('LENGTH',(b-a)/SR),('SOFFS',0)]:
        chunk=re.sub(rf'(?m)^      {field} .*$',f'      {field} {value:.12f}',chunk)
    chunk=re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m:m[1]+f'"{name}"',chunk)
    return re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)

staged.index=1
def original(name,x,iid):
    guid=lambda:'{'+str(uuid4()).upper()+'}'
    chunk=chunks[0]
    chunk=re.sub(r'\{[0-9A-F-]{36}\}',lambda m:guid(),chunk)
    chunk=re.sub(r'(?m)^      IID .*$',f'      IID {iid}',chunk)
    return staged(chunk,x,name)

old=[read(chunk)[0] for chunk in chunks]
_,intro_high,intro_drums,bed,kanye,savage,old_piano,guitar,strings,keys,outro=old
mix_before=sum(old)
back_before=mix_before-kanye-savage
# The sampled piano's first strike is 90 ms into the file. Put the
# strike itself on the drum grid instead of lining up the file edge.
advance=n(.091)
intro_high[:-advance]=intro_high[advance:].copy()
intro_high[-advance:]=0
bed_position=read(chunks[3])[1]
bed_stems={}
for name in ('drums','bass'):
    x=load(here/'rhythm'/f'{name}.wav')
    a=bed_position
    if a+len(x)>total:
        x=x[:total-a]
    y=bus()
    y[a:a+len(x)]=x
    bed_stems[name]=y
drums,bass=(bed_stems[name] for name in ('drums','bass'))

# Layer the new bass pickup into the hole at the first hook's exit, then
# let the recorded low end take over on beat one.
bass_part=bus()
for start,pitch,duration,velocity in json.loads((here/'notes.json').read_text())['Bass']:
    t=np.arange(n(duration+.12))/SR
    hz=440*2**((pitch-69)/12)
    amp=np.minimum(t/.019,1)*np.clip((duration+.12-t)/.12,0,1)
    wave=(np.sin(2*np.pi*hz*t)+.20*np.sin(4*np.pi*hz*t)+.062*np.sin(6*np.pi*hz*t))*amp
    wave=filt(wave.astype(np.float32),'lowpass',280)
    target=-23.7 if start<70 else -24.3
    wave*=db(target)*(.90+.10*(velocity/77))/rms(wave)
    add(bass_part,np.repeat(wave[:,None],2,axis=1),start)

def adjust_component(component,points):
    a,b=n(points[0][0]),n(points[-1][0])
    w=envelope(np.arange(a,b)/SR,points)[:,None]
    bed[a:b]+=(w-1)*component[a:b]

adjust_component(bass,[(21.96*bar,1),(22*bar,.76),(22.39*bar,1)])
adjust_component(bass,[(35.42*bar,1),(35.53*bar,.38),(35.94*bar,.38),(36.13*bar,1)])
# Pull the final kick, bass and chord texture back in stages as the
# upright takes over. Leave its first bar a little of the old pulse.
adjust_component(drums,[(63.98*bar,1),(64.44*bar,.88),(65.20*bar,.47),(66.25*bar,0),(67*bar,0)])
adjust_component(bass,[(63.98*bar,1),(64.41*bar,.68),(65.09*bar,.20),(66.12*bar,0),(67*bar,0)])
tonal=bed-drums-bass
a,b=n(64*bar),n(67*bar)
# Fade the full outgoing bed consistently after its local stem moves.
automate(bed,[(64*bar,1),(64.52*bar,.85),(65.22*bar,.26),(66.25*bar,0),(67*bar,0)])

# Briefly narrow only the tonal backing late in the lift. The kick and
# bass keep the exact pulse underneath the change of colour.
a,b=n(46.32*bar),n(48.29*bar)
t=np.arange(a,b)/SR
v=tonal[a:b]
s=band(v,245,2450)
w=envelope(t,[(46.32*bar,0),(46.95*bar,.27),(47.59*bar,.47),
              (48.10*bar,.12),(48.29*bar,0)])[:,None]
bed[a:b]+=(s-v)*w

# Free space for the rewritten lift and the Savage-to-Kanye phrase.
automate(old_piano,[(34.82*bar,1),(35*bar,0),(35.95*bar,0),(36.25*bar,1)])
for x,amount in [(guitar,.22),(strings,.52),(keys,.28)]:
    automate(x,[(21.92*bar,1),(22.12*bar,.60),(23.90*bar,.62),(24.45*bar,1)])
    automate(x,[(43.76*bar,1),(44.23*bar,amount),(47.62*bar,amount),
                (48.45*bar,.40),(49.2*bar,1)])
for x,amount in [(guitar,.03),(strings,.32),(keys,.06)]:
    automate(x,[(63.75*bar,1),(64.20*bar,amount),(65.1*bar,0),(67*bar,0)])

def print_part(path,lo,hi,groups,wet):
    source=band(load(path),lo,hi)
    padded=bus()
    padded[:min(len(padded),len(source))]=source[:len(padded)]
    out=bus()
    for a,b,target in groups:
        x=clip(padded,a*bar,b*bar)
        if rms(x)<1e-7:
            continue
        x=fade(level(x,target),.026,.40)
        add(out,x,a*bar)
    return Reverb(room_size=.46,damping=.62,wet_level=wet,
                  dry_level=.94,width=.90)(out.T,SR).T

piano=print_part(here/'Upright raw.wav',85,8400,
    [(1.30,3.08,-29.8),(5.1,6.75,-30.6),(13.5,14.65,-34.1),
     (21.48,24.9,-27.7),(34.81,36.8,-26.6),(43.96,48.84,-24.9),(63.04,64.14,-31)],.16)
cello=print_part(here/'Cello raw.wav',117,5800,
    [(1.5,3.18,-34.4),(5.23,6.83,-35),(13.55,14.6,-33.0),
     (22.03,24.6,-32.2),(34.78,36.75,-29.8),(44,49.1,-28.1),
     (55.5,56.42,-34.5),(63.3,65.3,-30.1)],.21)

fx=bus()
def echo(x,a,b,spacing,db_gain,feedback,count=2):
    tail=fade(band(clip(x,a,b),370,2950),.025,.17)
    for j in range(count):
        take=tail[:,::-1] if j%2==0 else tail
        add(fx,take*db(db_gain)*feedback**j,a+spacing*(j+1))

# Two filtered piano echoes, in different rhythmic roles. Echo source
# is instrumental throughout so the words can finish cleanly.
echo(piano,22.05*bar,22.54*bar,.75*beat,-11,.42,3)
echo(piano,35.52*bar,35.96*bar,.50*beat,-13,.32,2)
echo(piano,47.48*bar,48.01*bar,beat,-13,.33,2)

# Low-key stereo room tails glue the entrance and the handoff to the coda.
def room_tail(track,at,lookback,out_len,gain):
    tail=band(clip(track,at-lookback,at),260,5000)
    tail=np.pad(tail,((0,n(out_len)),(0,0)))
    wet=Reverb(room_size=.65,damping=.63,wet_level=1,dry_level=0,
               width=.94)(tail.T,SR).T[-n(out_len):]
    add(fx,fade(wet,.026,.38)*db(gain),at)

room_tail(intro_drums,6*bar,.51,.72,-5)
room_tail(drums,64*bar,.55,.93,-3.5)

# The outro's first E-major voicing foreshadows the last chorus as a
# soft reverse room tail. No percussion or vocal enters the effect.
chord=band(clip(outro,64*bar,64.23*bar),410,4300)
chord=np.pad(chord,((0,n(.68)),(0,0)))
room=Reverb(room_size=.62,damping=.57,wet_level=1,dry_level=0,width=.92)
reverse=room(chord.T,SR).T[-n(.63):][::-1].copy()
reverse=fade(level(reverse,-33),.32,.105)
add(fx,reverse,56*bar-.615)

changed={1:intro_high,3:bed,6:old_piano,7:guitar,8:strings,9:keys}
final=header
for index,chunk in enumerate(chunks):
    final+=staged(chunk,changed[index]) if index in changed else chunk
for i,(name,x) in enumerate([('Veer | Upright transition phrases',piano),
                              ('Veer | Cello transition phrases',cello),
                              ('Veer | Bass pickups',bass_part),
                              ('Veer | Transition echoes and room',fx)],12):
    final+=original(name,x,i)
final+='>\n'
(here/'When You Leave.rpp').write_text(final)
files={x.name for x in staging.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((staging if m[1] in files else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
after=sum(old)+piano+cello+bass_part+fx
sf.write(here/'Premaster.wav',after,SR,'FLOAT')

# Check that each seam keeps its low-end and rhythmic anchor.
rows=[]
for measure in [2,6,14,22,24,35,36,44,48,56,64]:
    t=measure*bar
    items=[]
    for x in (back_before,after-kanye-savage):
        lo=filt(clip(x,t-2.4*beat,t+2.1*beat),'lowpass',140)
        items.append([round(20*np.log10(max(1e-10,rms(clip(lo,(k+.4)*beat,(k+1.4)*beat)))),2)
                      for k in range(4)])
    rows.append([round(t,3),*items])
(here/'low-end-check.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Bass level before and after each handoff',rows,flush=True)
