"""Compare 21 Savage performances in the revised 87 BPM session."""
from pathlib import Path
import re
import sys
from uuid import uuid4

import numpy as np
from pedalboard import Compressor, Reverb
import soundfile as sf

here = Path(__file__).resolve().parent
song = here.parents[1]
root = song.parents[2]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load, stretch

project = root/'reaper/When You Leave'
stems = here.parent/'rebuild'
media = here/'Media'
bar = 240/87
shift = round(2*bar*SR)
frames = lambda t:round(t*SR)
dest = frames(18*bar)-shift

def curve(x,points):
    return x*np.interp(np.arange(len(x))/SR,*np.array(points).T).astype(np.float32)[:,None]

def crop(x,a,b):
    return x[frames(a):frames(b)].copy()

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def save(file,x):
    sf.write(media/file,x,SR,'FLOAT')

def guid():
    return '{'+str(uuid4()).upper()+'}'

def blocks(x):
    n = len(x)//8820
    return np.mean(x[:n*8820].reshape(n,8820,2)**2,axis=(1,2))

rpp = (here/'When You Leave.rpp').read_text()
header,*tracks = re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
verse_track = next(i for i,x in enumerate(tracks) if 'Media/Rebuild 04.wav' in x)
bed_track = next(i for i,x in enumerate(tracks) if 'Media/Rebuild 01.wav' in x)

def read_item(chunk,at,n):
    start = frames(float(re.search(r'(?m)^      POSITION (\S+)',chunk)[1]))
    length = frames(float(re.search(r'(?m)^      LENGTH (\S+)',chunk)[1]))
    offset = frames(float(re.search(r'(?m)^      SOFFS (\S+)',chunk)[1]))
    end = min(start+length,at+n)
    begin = max(start,at)
    out = np.zeros((n,2),np.float32)
    if begin>=end:
        return out
    name = re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    fpath = media/name if (media/name).exists() else project/'Media'/name
    with sf.SoundFile(fpath) as f:
        f.seek(offset+begin-start)
        out[begin-at:end-at] = f.read(end-begin,dtype='float32',always_2d=True)
    return out

# Take some bite out of the clap and hats during the verse while retaining
# the exact kick, snare and bass timing through both joins.
old_bed = load(project/'Media/Rebuild 01.wav')
old_position = frames(11.033469387755)
m0,m1 = 17*bar,31*bar
a,b = frames(m0)-old_position,frames(m1)-old_position
original = old_bed[a:b].copy()
top = filt(original,'highpass',2500)
blend = curve(top,[(0,0),(.95,.24),(m1-m0-2,.24),(m1-m0,0)])
old_bed[a:b] = original-blend
save('Runaway groove - verse EQ.wav',old_bed)
tracks[bed_track] = tracks[bed_track].replace('Rebuild 01.wav','Runaway groove - verse EQ.wav')

# Both separation windows include the full phrase around the splice.
# Crossfade in the space between lines, well inside the overlapping source.
early = load(here/'Creepin lead early.wav')
late = load(stems/'creepin lead.wav')
c_a,c_b,c_native = 127.315,156.318,127.475176
splice_a,splice_b = 146.60,146.94
c = crop(early,c_a-119,splice_b-119)
tail = crop(late,splice_a-143,c_b-143)
count = frames(splice_b)-frames(splice_a)
fadeup = np.linspace(0,1,count,dtype=np.float32)[:,None]
c[-count:] = c[-count:]*(1-fadeup)+tail[:count]*fadeup
c = np.concatenate((c,tail[count:]))
opts = {'Creepin':(c,c_a,c_native,98.0)}
mr = stems/'mr_right_now lead.wav'
if mr.exists():
    # Start on the actual verse after the hook. End on the first complete
    # line about leaving his feelings behind, ahead of its repeated pickup.
    opts['Mr Right Now'] = (crop(load(mr),34.03-33,64.64-33),34.03,33.564,86.04)

check_a = frames(14*bar)
check_b = frames(33*bar)
backing = sum(read_item(track,check_a,check_b-check_a)
              for i,track in enumerate(tracks) if i!=verse_track)
old_vocal = read_item(tracks[verse_track],check_a,check_b-check_a)

def voice_mix(label,args):
    x,first,anchor,bpm = args
    ratio = bpm/87
    pos = dest+frames((first-anchor)*ratio)
    x = stretch(x,len(x)*ratio/SR,label)
    x = band(x,83,11600)
    x -= filt(x,'highpass',4100)*.14
    x = Compressor(threshold_db=-21,ratio=1.45,attack_ms=12,release_ms=96)(x.T,SR).T
    x = fade(x,.019,.070)
    x = np.pad(x,((0,frames(.74)),(0,0)))
    x = Reverb(room_size=.50,damping=.62,wet_level=.12,dry_level=.92,width=.83)(x.T,SR).T
    x = fade(x,.009,.21)
    at = pos-check_a
    bed = backing[at:at+len(x)]
    active = blocks(band(x,380,4600))
    active = active>active.max()*.08
    v,b = [blocks(band(t,380,4600))[active].mean() for t in (x,bed)]
    x *= db(1.25-10*np.log10(v/b))
    v,b = [blocks(band(t,56,12500))[active].mean() for t in (x,bed)]
    print(label,round(pos/SR,3),round((pos+len(x))/SR,3),'broad ratio',round(10*np.log10(v/b),2))
    return x,pos

for label,params in opts.items():
    x,pos = voice_mix(label,params)
    preview = backing.copy()
    at = pos-check_a
    preview[at:at+len(x)] += x
    sf.write(here/f'{label} handoff.wav',fade(preview,.10,.24),SR,'FLOAT')
    if label=='Creepin':
        chosen,position = x,pos
sf.write(here/'Out for the Night handoff.wav',fade(backing+old_vocal,.10,.24),SR,'FLOAT')
save('21 Savage - Creepin.wav',chosen)
chunk = tracks[verse_track]
newname = '21 Savage | Creepin verse'
chunk = re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m:m[1]+f'"{newname}"',chunk)
chunk = chunk.replace('Rebuild 04.wav','21 Savage - Creepin.wav')
chunk = re.sub(r'(?m)^      POSITION .*$',f'      POSITION {position/SR:.12f}',chunk)
chunk = re.sub(r'(?m)^      LENGTH .*$',f'      LENGTH {len(chosen)/SR:.12f}',chunk)
tracks[verse_track] = chunk
header = header.replace('21 Savage | Out for the Night','21 Savage | Creepin')
revised = header+''.join(tracks)+'>\n'
(here/'Final.rpp').write_text(revised)
files = {p.name for p in media.glob('*.wav')}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda m:str((media if m[1] in files else project/'Media')/m[1]),revised)
render = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Final.mp3"',render)
(here/'Final Render.rpp').write_text(render)
