"""Join the two Kanye verses, then finish with a four-bar final hook."""
from pathlib import Path
import json
import re
import sys

import numpy as np
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt

project=root/'reaper/When You Leave'
old_stems=here.parent/'balance/Media'
media=here/'Media'
media.mkdir(exist_ok=True)
reference=here/'Reference.rpp'
rpp=(reference if reference.exists() else project/'When You Leave.rpp').read_text()
reference.write_text(rpp)
header,*chunks=re.split(r'(?m)(?=^  <TRACK )',rpp)
chunks[-1]=chunks[-1].rstrip().removesuffix('>').rstrip()+'\n'
total=round(float(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)',header)[1])*SR)
bar=240/87
def n(t):
    return round(t*SR)
def at(measure):
    return n(measure*bar)

join=at(44)
pre=at(52)
hook=at(60)
last=at(62)
outro=at(64)
old_pre=at(48)
old_hook=at(56)

def read(chunk):
    get=lambda f:n(float(re.search(rf'(?m)^      {f} (\S+)',chunk)[1]))
    a,ln,off=[get(f) for f in ('POSITION','LENGTH','SOFFS')]
    fn=re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    with sf.SoundFile(project/'Media'/fn) as f:
        f.seek(off)
        x=f.read(ln,dtype='float32',always_2d=True)
    assert a+len(x)<=total
    out=np.zeros((total,2),np.float32)
    out[a:a+len(x)]=x
    return out

def native(filename,raw_begin,length):
    with sf.SoundFile(old_stems/filename) as f:
        assert f.samplerate==SR
        # The existing separated take was verified against the original
        # waveform. Its alignment error was one sample.
        f.seek(n(raw_begin-187.86037)-1)
        return f.read(length,dtype='float32',always_2d=True)

def rms(x):
    return float(np.sqrt(np.mean(x*x)))

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def active_level(x,limits):
    x=band(x,*limits)
    step=n(.2)
    p=(x[:len(x)//step*step].reshape(-1,step,2)**2).mean((1,2))
    return 10*np.log10(p[p>p.max()*.075].mean())

def gains(x,points):
    pts=np.array(points)
    return x*np.interp(np.arange(len(x)),pts[:,0],pts[:,1]).astype(np.float32)[:,None]

def replace(chunk,x,file):
    active=np.flatnonzero(np.max(np.abs(x),axis=1)>1e-7)
    a,b=max(0,int(active[0])-32),min(len(x),int(active[-1])+33)
    sf.write(media/file,x[a:b],SR,'FLOAT')
    for field,value in [('POSITION',a/SR),('LENGTH',(b-a)/SR),('SOFFS',0)]:
        chunk=re.sub(rf'(?m)^      {field} .*$',f'      {field} {value:.12f}',chunk)
    return re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)

bed_before,lead_before=(read(chunks[i]) for i in (3,4))
source_anchor=258.72
preroll=n(.052)
overlap=n(.11)
n_music=last-join+preroll+overlap
original=native('Runaway instrumental.wav',source_anchor-preroll/SR,n_music)
direct=native('Kanye lead.wav',source_anchor-preroll/SR,n_music+n(.48))

# Keep one uninterrupted source performance through the new verse, sung
# reprise, and the opening two bars of the final chorus. Match the adjoining
# vocal and backing bands independently to keep the two verses in one pocket.
report={}
for label,x,baseline,limits in [
    ('voice',direct,lead_before,(400,4900)),
    ('backing',original,bed_before,(45,12500))
]:
    starts=[preroll,pre-join+preroll,hook-join+preroll]
    ends=starts[1:]+[last-join+preroll]
    refs=[(at(36),join),(old_pre,old_hook),(old_hook,at(58))]
    dbs=[active_level(baseline[a:b],limits)-active_level(x[s:e],limits)
         for (a,b),s,e in zip(refs,starts,ends)]
    f=[db(d) for d in dbs]
    points=[(0,f[0]),(starts[1]-n(.18),f[0]),(starts[1]+n(.24),f[1]),
            (starts[2]-n(.16),f[1]),(starts[2]+n(.24),f[2]),(len(x),f[2])]
    x[:]=gains(x,points)
    report[label]=[round(float(d),2) for d in dbs]

# The old bed's tail resolves onto the new E downbeat. At the short hook
# edit, give the outgoing harmony a fraction of a beat as the final two
# bars take over, with the kick kept on the grid.
bed=bed_before.copy()
bed_start=join-preroll
bed[bed_start:last+overlap]=0
old_tail=bed_before[bed_start:join+n(.065)]
bed[bed_start:join+n(.065)]+=fade(old_tail,0,len(old_tail)/SR)
incoming=fade(original,(preroll+n(.033))/SR,overlap/SR)
bed[bed_start:bed_start+len(incoming)]+=incoming
bed[last:last+overlap]+=fade(bed_before[last:last+overlap],overlap/SR,0)

# Preserve the first verse's last word. The new first word is admitted
# after the preceding performer on the source. Cut the final hook between
# complete lines and keep its closing couplet at its original timeline spot.
lead=lead_before.copy()
lead[join+n(.24):last+n(.40)]=0
start_word=join+n(258.98-source_anchor)
new_vocal_end=join+n(308.78-source_anchor)
v=direct[start_word-bed_start:new_vocal_end-bed_start]
lead[start_word:new_vocal_end]+=fade(v,.018,.057)
lead[last+n(.40):last+n(.51)]=fade(lead[last+n(.40):last+n(.51)],.048,0)

changes={3:(bed,'Runaway continuous verses and hook.wav'),
         4:(lead,'Kanye combined verses and hook.wav')}
for idx,name in [(7,'Guitar'),(8,'Strings'),(9,'Keys'),(11,'Upright'),(12,'Cello'),(14,'Echoes')]:
    x=read(chunks[idx])
    if idx==14:
        # Keep the quiet reverse piano cue with the final chorus.
        pickup=x[old_hook-n(.625):old_hook+n(.04)].copy()
    if idx==12:
        # The E and B common tones carry across the two verse recordings.
        # The old melodic lift is cleared as the lead comes forward.
        common=fade(x[join:join+n(1.45)],.065,1.00)*db(-6)
    a,b=join,last
    x[a-n(.24):a]=fade(x[a-n(.24):a],0,.24)
    x[a:b]=0
    x[b:b+n(.24)]=fade(x[b:b+n(.24)],.24,0)
    if idx==12:
        x[join:join+len(common)]+=common
    if idx==14:
        start=hook-n(.625)
        x[start:start+len(pickup)]+=pickup
    changes[idx]=(x,f'{name} - combined verse arrangement.wav')

markers=[
    (join,'Kanye | Verse continuation'),
    (pre,'Kanye | Sung reprise'),
    (hook,'Final chorus | Four bars')
]
for marker_id,(position,label) in zip((9,10,11),markers):
    header=re.sub(rf'(?m)^(  MARKER {marker_id} )\S+ "[^"]+"',
                  lambda m:f'{m[1]}{position/SR:.10f} "{label}"',header)
final=header
for i,chunk in enumerate(chunks):
    final+=replace(chunk,*changes[i]) if i in changes else chunk
final+='>\n'
(here/'When You Leave.rpp').write_text(final)
names={p.name for p in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((media if m[1] in names else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
before=sum(read(chunk) for chunk in chunks)
after=sum(changes[i][0] if i in changes else read(chunk) for i,chunk in enumerate(chunks))
for t in (115,178):
    a,b=n(t),n(t+1)
    assert np.array_equal(before[a:b],after[a:b])
sf.write(here/'Premaster.wav',after,SR,'FLOAT')
for t in (join,last):
    a,b=t-n(.689655),t+n(.689655)
    lows=band((after-lead)[a:b],45,155)
    report[f'Low end around {t/SR:.3f}']=[round(20*np.log10(rms(x)),2) for x in np.array_split(lows,2)]
report['timing_seconds']={label:round(position/SR,4) for position,label in markers}
report['timing_seconds']['Original piano outro']=round(outro/SR,4)
(here/'arrangement-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
