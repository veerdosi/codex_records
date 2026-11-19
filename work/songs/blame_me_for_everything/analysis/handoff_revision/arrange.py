"""Build the contextual opening, shorter verse handoff and original coda."""
from pathlib import Path
from fractions import Fraction
from uuid import uuid4
import json
import re
import sys

import numpy as np
from pedalboard import Reverb
from scipy.signal import resample_poly
import soundfile as sf

here = Path(__file__).resolve().parent
song = here.parents[1]
root = here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

project = root/'reaper/When You Leave'
media = here/'Media'
media.mkdir(exist_ok=True)
ref = here/'Reference.rpp'
old_rpp = (ref if ref.exists() else project/'When You Leave.rpp').read_text()
ref.write_text(old_rpp)
header,*chunks = re.split(r'(?m)(?=^  <TRACK )',old_rpp)
beat = 60/87
bar = 4*beat
def n(t):
    return round(t*SR)
def guid():
    return '{'+str(uuid4()).upper()+'}'
def clip(x,a,b):
    return x[n(a):n(b)].copy()
def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)
def shape(x,points):
    return x*np.interp(np.arange(len(x))/SR,*np.array(points).T).astype(np.float32)[:,None]
def gated_db(x):
    step=8820
    p=np.mean(x[:len(x)//step*step].reshape(-1,step,2)**2,axis=(1,2))
    return 10*np.log10(np.mean(p[p>p.max()*.075]))
def match(x,target):
    return x*db(target-gated_db(x))

old_size=n(float(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)',header)[1]))
opening=n(6*bar)
pre=n(8*bar)
cut_a,cut_b=n(28*bar),n(30*bar)
final_hook=n(42*bar)
outro=n(50*bar)+2*pre-(cut_b-cut_a)
extra=n(4*bar)
total=old_size+2*pre-(cut_b-cut_a)+extra
pos_savage=n(43.957505668934)+pre
pos_kanye=cut_a+pre
pos_reprise=final_hook+pre-(cut_b-cut_a)

def empty(length=total):
    return np.zeros((length,2),np.float32)
def add(bus,x,at):
    assert 0<=at<=at+len(x)<=len(bus),(at,len(x),len(bus))
    bus[at:at+len(x)] += x
def old_track(chunk):
    get=lambda key: n(float(re.search(rf'(?m)^      {key} (\S+)',chunk)[1]))
    file=re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    at,length,offset=(get(k) for k in ('POSITION','LENGTH','SOFFS'))
    x=empty(old_size)
    with sf.SoundFile(project/'Media'/file) as f:
        f.seek(offset)
        take=f.read(length,dtype='float32',always_2d=True)
    add(x,take,at)
    return x
def remap(x):
    blank=empty(pre)
    return np.concatenate((x[:opening],blank,x[opening:cut_a],
                           x[cut_b:final_hook],blank,x[final_hook:],empty(extra)))

groove,old_vocal,old_21,guitar,strings,keys=(old_track(chunks[i]) for i in (3,5,6,7,8,9))
intro_drums=old_track(chunks[2])
intro_drums[opening-n(.032):opening]=fade(intro_drums[opening-n(.032):opening],0,.032)
intro_drums[opening:]=0
lead=remap(old_vocal)
lead[opening:opening+2*pre+n(.22)]=0

# Reduce the recorded piano that was competing with Savage and retain the
# low end and drums. Reintroduce that timbre as deliberately placed replies.
piano_stem=load(here/'piano_separation/piano.wav')
raw_bed=load(song/'stems/runaway_bed_source_instrumental.wav')
patch_start,patch_end=n(238.91-214),n(240.40-214)
period=n(22.07)
for track in (piano_stem,raw_bed):
    w=fade(np.ones_like(track[patch_start:patch_end]),.11,.14)
    track[patch_start:patch_end]=(1-w)*track[patch_start:patch_end]+w*track[patch_start-period:patch_end-period]
native=n(.58)
a,b=n(14*bar),cut_a+n(.17)
size=b-a
reference=raw_bed[native:native+size]
piano_reduction=band(piano_stem[native:native+size],440,6400)
ref_low=filt(reference,'lowpass',285)
bed_low=filt(groove[a:b],'lowpass',285)
positions,gains=[],[]
for i in range(0,size,n(bar)):
    j=min(i+n(bar),size)
    r,s=ref_low[i:j],bed_low[i:j]
    gain=(r*s).sum()/max((r*r).sum(),1e-8)
    positions.append((i+j)/2/SR)
    gains.append(float(np.clip(gain,.35,.8)))
piano_reduction=shape(piano_reduction,list(zip(positions,gains)))
piano_reduction=shape(piano_reduction,[(0,0),(1.5*bar,0),(2*bar,.82),
                                      (13.7*bar,.82),(size/SR,.64)])
groove[a:b]-=piano_reduction
groove_before=groove[cut_a:cut_a+n(.18)].copy()

# Take the old first chorus out as a block. The fresh native passage below
# supplies the whole pre-chorus and hook, continuously.
groove[:a]=0
groove[a:a+n(.18)]=fade(groove[a:a+n(.18)],.18,0)
bed=remap(groove)
add(bed,fade(groove_before,0,.18),pos_kanye)
bed[pos_kanye:pos_kanye+n(.13)]+=fade(groove[cut_b:cut_b+n(.13)],.13,0)-groove[cut_b:cut_b+n(.13)]

# Keep these older accompaniment parts lower during Savage's phrases,
# and give the new piano sole melodic emphasis in the last bar.
for track,amount in ((guitar,.65),(strings,.80),(keys,.75)):
    track[:]=shape(track,[(0,1),(15.5*bar,1),(16.1*bar,amount),(26.8*bar,amount),
                         (27.1*bar,0),(28*bar,0),(30*bar,.65),(31*bar,1)])
guitar,strings,keys=map(remap,(guitar,strings,keys))
for track in (guitar,strings,keys):
    track[outro:outro+n(2*bar)]=fade(track[outro:outro+n(2*bar)],0,2*bar)
    track[outro+n(2*bar):]=0

def two_stems(raw_a,dur,source_a,source_lead,source_bed):
    lo=n(raw_a-source_a)
    ln=n(dur)
    return source_lead[lo:lo+ln].copy(),source_bed[lo:lo+ln].copy()

def mix_passage(voice,music,at,is_opening):
    music=band(music,32,16300)
    voice=band(voice,75,12700)
    music=match(music,-17.2)
    voice=match(voice,-18.6)
    if is_opening:
        # The spoken thought opens quietly, then the original hook widens.
        music=shape(music,[(0,.88),(pre/SR-2,.98),(pre/SR+1,1.02)])
        voice=shape(voice,[(0,.92),(pre/SR-1,.95),(pre/SR+.30,1.05)])
    add(bed,fade(music,.070,.13),at)
    add(lead,fade(voice,.036,.095),at)

voice,music=two_stems(60.10,16*bar+.13,58.7,load(here/'runaway lead.wav'),load(here/'runaway backing.wav'))
mix_passage(voice,music,opening,True)
old_balance=here.parent/'balance/Media'
voice,music=two_stems(280.79,8*bar+.10,187.86037,
                     load(old_balance/'Kanye lead.wav'),load(old_balance/'Runaway instrumental.wav'))
mix_passage(voice,music,pos_reprise,False)

# Use a single strike from the Runaway recording for the in-verse answers.
# It plays in breath gaps on the eighth-note grid and through the turnaround.
with sf.SoundFile(song/'sources/runaway.wav') as f:
    f.seek(n(.082))
    one=f.read(n(1.16),dtype='float32',always_2d=True)
answers=empty()
notes=[(16,3.5,-5,-31.2),(18,0,0,-31.5),(20,0,-8,-32),
       (21,3.5,0,-31.0),(24,3.5,-5,-31.5),(25,3.5,-1,-32),
       (27,0,0,-26.8),(27,2,-8,-29.5)]
for measure,beat_pos,pitch,level in notes:
    ratio=Fraction(2**(-pitch/12)).limit_denominator(90)
    note=resample_poly(one,ratio.numerator,ratio.denominator,axis=0).astype(np.float32)
    note=band(note,375,6200)
    note=fade(note[:n(.65 if measure<27 else 1.02)],.006,.22)
    note=match(note,level)
    at=n(measure*bar+beat_pos*beat)+pre
    add(answers,note,at)
    if measure==27:
        add(answers,note[:,::-1]*db(-15),at+n(.5*beat))

# The newly composed upright begins over the fading end of the groove.
piano=band(load(here/'Veer piano outro raw.wav'),48,10100)
piano=Reverb(room_size=.47,damping=.59,wet_level=.19,dry_level=.90,width=.85)(piano.T,SR).T
piano=fade(match(piano,-23.1),.012,.78)
out=empty()
add(out,piano[:total-outro],outro)

sav=empty()
x=load(here/'Savage tuned.wav')
add(sav,x,pos_savage)
backing=bed+guitar+strings+keys+answers
levels={}
for name,vocal,a,b in [('Savage',sav,pos_savage,pos_savage+len(x)),
                       ('Kanye pre-chorus',lead,opening,opening+pre),
                       ('Kanye first hook',lead,opening+pre,opening+2*pre),
                       ('Kanye reprise',lead,pos_reprise,pos_reprise+pre)]:
    s=slice(a,b)
    v,i=vocal[s],backing[s]
    step=8820
    def power(x):
        f=band(x,400,4900)
        return np.mean(f[:len(f)//step*step].reshape(-1,step,2)**2,axis=(1,2))
    pp=power(v)
    active=pp>pp.max()*.07
    delta=10*np.log10(pp[active].mean()/power(i)[active].mean())
    gain=np.clip(1.5-delta,-3,3)
    vocal[s]*=db(gain)
    levels[name]=[round(a/SR,3),round(b/SR,3),round(float(delta+gain),2)]
print('Vocal presence ratios by passage',levels,flush=True)

tracks=[
    ('Intro | Pitched Runaway piano',remap(old_track(chunks[0]))),
    ('Intro | High Runaway piano',remap(old_track(chunks[1]))),
    ('Intro | Drum reveal',remap(intro_drums)),
    ('Runaway | Instrumental',bed),('Kanye West | Lead',lead),
    ('21 Savage | Creepin, tuned',sav),('Runaway | Piano answers',answers),
    ('Veer | Guitar',guitar),('Veer | Strings',strings),('Veer | Keys',keys),
    ('Veer | Original upright piano outro',out),
]
header=header.split('  MARKER ',1)[0]
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {total/SR:.12f} 0 1000',header)
markers=[
    (0,'Low piano opening'),(n(2*bar),'Runaway piano reveal'),
    (opening,'Kanye | Sung setup'),(opening+pre,'First chorus'),
    (n(14*bar)+pre,'Guitar answers'),(n(16*bar)+pre,'21 Savage | Creepin'),
    (n(27*bar)+pre,'Piano turnaround'),(pos_kanye,'Kanye | Opening Runaway verse'),
    (n(38*bar)+pre-(cut_b-cut_a),'Instrumental lift'),(pos_reprise,'Kanye | Sung reprise'),
    (pos_reprise+pre,'Final chorus'),(outro,'Veer | Original piano outro'),
]
for idx,(at,name) in enumerate(markers,1):
    header+=f'  MARKER {idx} {at/SR:.10f} "{name}" 0 0 1 B {guid()} 0 1\n'

for i,(name,x) in enumerate(tracks,1):
    file=f'Handoff {i:02}.wav'
    active=np.flatnonzero(np.max(np.abs(x),axis=1)>1e-7)
    a,b=max(0,int(active[0])-32),min(len(x),int(active[-1])+33)
    sf.write(media/file,x[a:b],SR,'FLOAT')
    header+=f'''  <TRACK {guid()}
    NAME "{name}"
    VOLPAN 1 0 -1 -1 1
    MAINSEND 1 0
    NCHAN 2
    <ITEM
      POSITION {a/SR:.12f}
      LENGTH {(b-a)/SR:.12f}
      LOOP 0
      FADEIN 1 0 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0 0 1 0 0 0 1 0 0 1 0 0
      NAME "{name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      IID {i}
      IGUID {guid()}
      GUID {guid()}
      <SOURCE WAVE
        FILE "Media/{file}"
      >
    >
  >
'''
rpp=header+'>\n'
(here/'When You Leave.rpp').write_text(rpp)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',rpp)
(here/'Render.rpp').write_text(render)
sf.write(here/'Premaster.wav',sum(x for _,x in tracks),SR,'FLOAT')
(here/'arrangement-check.json').write_text(json.dumps({
    'sections':{name:round(at/SR,4) for at,name in markers},'length':total/SR,
    'presence':levels
},indent=2)+'\n')
