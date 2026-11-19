"""Rebuild the opening from Runaway's piano and backing, then stage REAPER."""
from pathlib import Path
import re
import sys
from uuid import uuid4

import numpy as np
from pedalboard import Reverb
from scipy.signal import resample_poly
import soundfile as sf

here = Path(__file__).resolve().parent
song = here.parents[1]
root = song.parents[2]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

project = root/'reaper/When You Leave'
old_project = here/'Before revision.rpp'
old_rpp = (old_project if old_project.exists() else project/'When You Leave.rpp').read_text()
old_project.write_text(old_rpp)
media = here/'Media'
media.mkdir(exist_ok=True)
old_hook = 8*240/87
shift = round(2*240/87*SR)
bar = 240/87

def frames(t):
    return round(t*SR)

def clip(x,a,b):
    return x[frames(a):frames(b)].copy()

def curve(x,points):
    return x*np.interp(np.arange(len(x))/SR,*np.array(points).T).astype(np.float32)[:,None]

def match(x,target,step=4410):
    n = len(x)//step
    p = (x[:n*step].reshape(n,-1)**2).mean(1)
    return x*db(target-10*np.log10(p[p>p.max()*.075].mean()))

def guid():
    return '{'+str(uuid4()).upper()+'}'

def add(x,clip,at):
    n = frames(at)
    assert n>=0 and n+len(clip)<=len(x)
    x[n:n+len(clip)] += clip

def write(name,x):
    sf.write(media/name,x,SR,'FLOAT')

with sf.SoundFile(song/'sources/runaway.wav') as f:
    piano_source = f.read(frames(4*bar+.09),dtype='float32',always_2d=True)
source = load(song/'stems/runaway_bed_source_instrumental.wav')
source = clip(source,225.62-214,225.62-214+4*bar+.20)
source = match(source,-17.15,8820)
length = len(source)/SR
low = filt(source,'lowpass',420)
mid = filt(source,'lowpass',1800)
old_open = (curve(low,[(0,.90),(4.3,.64),(8.2,.13),(length,0)])+
            curve(mid,[(0,.10),(4.3,.36),(8.2,.67),(length,0)])+
            curve(source,[(0,0),(5.6,0),(8.2,.20),(length,1)]))
old_open = fade(old_open,.45,.22)
old_open *= np.interp(4*bar+np.arange(len(old_open))/SR,
                      [0,5*bar,7*bar,8*bar-.22,8*bar+.26],
                      [1,1,db(.65),db(.65),db(-1.25)]).astype(np.float32)[:,None]

# Let the first strikes speak over the low part of the backing, then reveal
# the clap and bass texture on the same pulse the chorus will use.
late = (curve(filt(source,'lowpass',145),[(0,.31),(2,.44),(5.5,.15),(8,0),(length,0)])+
        curve(mid,[(0,.07),(2,.15),(5.5,.56),(8.25,.33),(length,0)])+
        curve(source,[(0,0),(3.2,0),(5.52,.12),(8.25,.53),(10.4,.88),(length,.90)]))
late = fade(late,.32,.22)
bright = match(piano_source,-23.2)
bright = curve(bright,[(0,1),(3.75,.99),(6.9,.94),(9.3,.85),(4*bar,.79)])
bright = fade(bright,.008,.60)
write('Intro high piano.wav',bright)

# A single low piano strike and its reversed room tail foreshadow the
# recognizable high note. Both use the same recording at different octaves.
take = clip(piano_source,.079,.73)
low_piano = resample_poly(fade(take,.008,.10),8,1,axis=0).astype(np.float32)
low_piano = filt(filt(low_piano,'highpass',78),'lowpass',1200)
low_piano = fade(low_piano,.025,1.25)
low_piano = match(low_piano,-24)
room = Reverb(room_size=.69,damping=.58,wet_level=.33,dry_level=.80,width=.9)
low_piano = room(low_piano.T,SR).T
shadow = np.zeros((frames(2*bar+.58),2),dtype=np.float32)
add(shadow,low_piano[:frames(4.65)],.06)
repeat = fade(low_piano[:frames(1.46)],.03,.52)
add(shadow,repeat[:,::-1]*db(-7.0),2*bar-2.5*60/87)
reverse = fade(clip(low_piano,0,1.38)[::-1],.68,.09)
add(shadow,reverse*db(-5.0),2*bar-1.31)
shadow = fade(shadow,.009,.48)
write('Intro low piano.wav',shadow)

header,*chunks = re.split(r'(?m)(?=^  <TRACK )',old_rpp)
chunks[-1] = chunks[-1].rstrip().removesuffix('>').rstrip()+'\n'
old_groove = chunks[0]
old_groove_start = frames(float(re.search(r'(?m)^      POSITION (\S+)',old_groove)[1]))
hook_sample = frames(old_hook)
old_overlap_offset = hook_sample-frames(4*bar)
transition_len = frames(.24)
overlap = np.pad(old_open[old_overlap_offset:old_overlap_offset+transition_len],
                 ((0,transition_len-len(old_open[old_overlap_offset:old_overlap_offset+transition_len])),(0,0)))
with sf.SoundFile(project/'Media/Rebuild 01.wav') as f:
    f.seek(hook_sample-old_groove_start)
    first = f.read(transition_len,dtype='float32',always_2d=True)-overlap
intro_bed = np.zeros((frames(4*bar)+transition_len+2,2),dtype=np.float32)
intro_bed[:len(late)] = late
intro_bed[frames(4*bar):frames(4*bar)+transition_len] += first
intro_bed = intro_bed[:frames(4*bar)+transition_len]
write('Intro drum reveal.wav',intro_bed)

def item_track(name,file,position,iid):
    with sf.SoundFile(media/file) as f:
        length = len(f)/SR
    return f'''  <TRACK {guid()}
    NAME "{name}"
    VOLPAN 1 0 -1 -1 1
    MAINSEND 1 0
    NCHAN 2
    <ITEM
      POSITION {position/SR:.12f}
      LENGTH {length:.12f}
      LOOP 0
      FADEIN 1 0 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0 0 1 0 0 0 1 0 0 1 0 0
      NAME "{name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      IID {iid}
      IGUID {guid()}
      GUID {guid()}
      <SOURCE WAVE
        FILE "Media/{file}"
      >
    >
  >
'''

def move(chunk,trim_start):
    """Start at the requested original timeline sample, then shift earlier."""
    values = {}
    for field in ('POSITION','LENGTH','SOFFS'):
        values[field] = frames(float(re.search(rf'(?m)^      {field} (\S+)',chunk)[1]))
    skipped = max(0,trim_start-values['POSITION'])
    values['POSITION'] += skipped-shift
    values['LENGTH'] -= skipped
    values['SOFFS'] += skipped
    assert values['POSITION']>=0 and values['LENGTH']>0
    for field,n in values.items():
        chunk = re.sub(rf'(?m)^      {field} .*$',f'      {field} {n/SR:.12f}',chunk)
    return chunk

duration = 56*bar+1-shift/SR
header = re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {duration:.12f} 0 1000',header)
base,markers = header.split('  MARKER ',1)
base += f'  MARKER 1 0.0000000000 "Low piano opening" 0 0 1 B {guid()} 0 1\n'
base += f'  MARKER 2 {shift/SR:.10f} "Runaway piano reveal" 0 0 1 B {guid()} 0 1\n'
for marker in ('  MARKER '+markers).splitlines()[2:]:
    m = re.match(r'(  MARKER \d+ )(\S+)( .*)',marker)
    assert m, marker
    base += f'{m[1]}{float(m[2])-shift/SR:.10f}{m[3]}\n'
base += item_track('Intro | Pitched Runaway piano','Intro low piano.wav',0,10)
base += item_track('Intro | High Runaway piano','Intro high piano.wav',shift,11)
base += item_track('Intro | Runaway drum reveal','Intro drum reveal.wav',shift,12)
for i,trim_start in enumerate([hook_sample+transition_len,frames(146),0,0,
                               frames(24),frames(24),0]):
    base += move(chunks[i],trim_start)
base += '>\n'
(here/'When You Leave.rpp').write_text(base)
staged_files = {p.name for p in media.glob('*.wav')}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda m:str((media if m[1] in staged_files else project/'Media')/m[1]),base)
render = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
