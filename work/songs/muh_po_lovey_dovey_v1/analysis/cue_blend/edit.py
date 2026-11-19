"""Arrange the upright as a handoff between Farebi's existing accents."""
from pathlib import Path
import json
import re
import sys

import numpy as np
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
sys.path.insert(0, str(stage.parent/'piano_returns'))
from score import print_piano

version = int(sys.argv[1])
title = f'Muh Pe Lovey Dovey v{version}'
project = root/'reaper'/title
destination = stage/f'v{version}'
(destination/'Media').mkdir(parents=True,exist_ok=True)
reference = destination/'Source.rpp'
source = (reference if reference.is_file() else project/(title+'.rpp')).read_text()
timing = json.loads((stage.parent/'piano_returns'/('fixed' if version==1 else 'native')/'piano.json').read_text())

# Times are seconds from the existing cue. Matching E and B on the
# opening sonority lets Farebi supply the third. Each answer then follows
# the upper chord tones that are actually present in that turnaround.
encore = [
    (.09,.32,64,71,0),(.10,.29,71,67,0),(.62,.21,67,64,0),
    (.66,.19,71,59,0),(1.72,.24,71,72,0),(1.73,.21,76,64,0),
    (2.27,.22,71,67,0),(2.27,.20,75,62,0),
] if version==1 else [
    (.04,.32,64,71,0),(.05,.29,71,67,0),(.60,.21,67,64,0),
    (.63,.19,71,59,0),(1.83,.28,72,70,0),(1.84,.23,76,65,0),
    (2.50,.22,71,67,0),(2.50,.20,76,61,0),
]
calm = [
    (.045,.32,64,71,0),(.050,.29,71,67,0),(.695,.22,67,64,0),
    (.71,.18,71,59,0),(1.79,.28,71,71,0),(1.80,.25,75,64,0),
    (2.48,.25,75,65,0),(2.49,.23,80,62,0),
] if version==1 else [
    (.08,.32,64,71,0),(.09,.29,71,67,0),(.77,.21,67,64,0),
    (.79,.18,71,59,0),(1.82,.24,71,71,0),(1.84,.22,75,63,0),
    (2.53,.25,64,67,0),(2.54,.22,71,62,0),
]
# Follow the descending third of Farebi's B7 → Bm7. Let the notes
# brighten as the original chord tails give way to the E resolution.
scale=60/(85 if version==1 else 90)
coda=[(t*scale,d*scale,n,v,p) for t,d,n,v,p in [
    (.25,.66,66,68,-.23),(.25,.65,75,65,.25),(.75,.42,69,60,-.33),
    (1.75,1.35,59,68,0),(1.75,1.34,62,66,-.28),(2,1.1,66,68,.36),
    (2.75,1.12,69,65,-.31),(3.5,.69,71,66,.37),
    (4.5,2.17,52,76,0),(4.5,2.28,59,69,-.29),
    (4.62,1.9,67,68,.39),(4.8,1.7,71,65,-.42),
    (5.25,1.29,76,61,.40),(7.1,1.68,64,62,-.27),
    (7.2,1.55,71,57,.37)
]]
config=[
    ('Encore piano answer',encore,-25.1,4050,(.11,.046)),
    ('Calm piano answer',calm,-24.9,4050,(.11,.046)),
    ('Farebi piano resolution',coda,-24.2,6400,(.22,.11,.052)),
]
for (old,position,duration),(name,events,db,treble,echo) in zip(timing,config):
    score=[(t/.75,d/.75,n,v,p) for t,d,n,v,p in events]
    # Seconds were chosen against the post-warp audio. This clock
    # therefore converts the written beat units directly to seconds.
    new,_,_= print_piano(destination,name,score,position,lambda t:t,duration,db,treble=treble,echo=echo)
    assert source.count(old)==2
    source=source.replace(old,new)

def env(track):
    match=re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',track)
    assert match
    return match[0]

def set_rides(track,changes):
    original=env(track)
    points=np.array([(float(a),float(b)) for a,b in re.findall(r'^      PT (\S+) (\S+) 0$',original,re.M)])
    positions=sorted(set(np.r_[points[:,0],[t for t,_ in changes]]))
    values=np.interp(positions,points[:,0],points[:,1])
    # Every ride starts and ends at unity relative to the original.
    values*=10**(np.interp(positions,*np.asarray(changes).T)/20)
    prefix=re.sub(r'^      PT .*\n','',original,flags=re.M).removesuffix('    >')
    points=''.join(f'      PT {t:.12f} {v:.12f} 0\n' for t,v in zip(positions,values))
    return track.replace(original,prefix+points+'    >')

parts=re.split(r'(?m)(?=^  <TRACK )',source)
music=parts[3]
assert 'NAME "Farebi | Music"' in music
moves=[]
for (_,start,_),(name,events,*_) in zip(timing,config):
    if 'resolution' in name:
        # Thin the synth bed a little at first, progressively opening
        # room for the existing drum and bass tails as the piano resolves.
        moves.extend((start+t,db) for t,db in [(-.08,0),(.52,-1.5),(1.17,-2.8),
                     (2.49,-5.2),(3.31,-9.5),(4.58,-9.5),(4.66,0)])
    else:
        # Duck the melodic sample around the answer, with the kick and
        # bass continuing independently. Restore the original before
        # its next figure so it sounds like a call and response.
        moves.extend((start+t,db) for t,db in [(-.055,0),(.115,-2.1),(.44,-1.4),
                     (.86,0),(1.49,0),(1.75,-2.5),(2.09,-2.1),
                     (2.37,-3.1),(2.67,-2.5),(3.03,0)])
parts[3]=set_rides(music,moves)
text=''.join(parts)
(destination/'Portable.rpp').write_text(text)

def resolve(m):
    for directory in (destination/'Media',project/'Media',
                      stage.parents[1]/'previous_exports/Before piano integration'/title/'Media'):
        if (directory/m[1]).is_file():
            return f'FILE "{directory/m[1]}"'
    raise FileNotFoundError(m[1])

for name,ext in [('Premaster','wav'),('Master','mp3')]:
    draft=re.sub(r'FILE "Media/([^"]+)"',resolve,text)
    draft=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{destination/name}.{ext}"',draft)
    if ext=='wav':
        draft=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',draft)
        draft=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',draft)
        draft=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',draft)
    (destination/f'{name}.rpp').write_text(draft)
