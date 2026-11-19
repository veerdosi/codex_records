"""Shape the backing around the measured vocal entrances, lifts and gaps."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from uuid import uuid4

import numpy as np
import soundfile as sf

here=Path(__file__).resolve().parent
song=here.parents[1]
root=song.parents[2]
title='Sunn Raha Hai (Under Glass)'
session=root/'reaper'/title
before=here/'Before.rpp'
if not before.exists():
    before.write_bytes((session/(title+'.rpp')).read_bytes())
media=here/'Media'
media.mkdir(exist_ok=True)
sys.path.insert(0,str(here.parent/'shoegaze'))
from arrange_shoegaze import BEAT, GUITAR, SR, fade, filt, load, wet, write_midi

# dB moves on the backing, independently drawn against Shreya's phrases.
Rides={
    'Glide guitars':[
        [(40.20,0),(40.45,.75),(40.94,2.55),(41.29,2.76),(41.75,1.15),(42.17,0)],
        [(83.24,0),(83.66,.80),(84.02,2.40),(84.15,2.10),(84.44,0)],
        [(108.12,0),(108.45,1.5),(108.82,.9),(109.28,0)],
        [(118.70,0),(119.05,-1.3),(119.29,.55),(119.60,2.65),(119.88,2.30),(120.24,.60),(120.55,0)],
        [(142.45,0),(142.81,.56),(143.38,2.8),(143.94,3.2),(144.57,1.6),(145.00,0)],
        [(149.38,0),(149.70,.64),(150.02,1.85),(150.17,1.4),(150.52,0)],
        [(157.35,0),(157.92,1.35),(158.73,1.5),(159.12,.75),(159.58,-.90),(160.35,-1.25),(160.79,0)],
        [(168.19,0),(169.00,.57),(169.49,1.45),(170.12,.80),(170.64,-.85),(171.29,0)],
    ],
    'Guitar motif and air':[
        [(83.23,0),(83.62,1.45),(84.07,2.05),(84.45,0)],
        [(149.32,0),(149.73,1.7),(150.16,2.30),(150.52,0)],
        [(170.15,0),(170.69,1.1),(171.26,1.0),(171.76,0)],
    ],
    'Picked bass':[
        [(40.24,0),(40.69,.62),(41.16,.86),(41.72,0)],
        [(119.05,0),(119.38,.4),(119.75,.9),(120.21,0)],
        [(142.78,0),(143.35,.6),(143.9,1.0),(144.56,0)],
        [(157.56,0),(158.12,.55),(159.10,.76),(159.62,0)],
    ],
    'Live kit':[
        [(83.5,0),(83.81,-.95),(84.12,-1.2),(84.28,0)],
        [(149.48,0),(149.79,-.85),(150.11,-1.2),(150.30,0)],
        [(159.29,0),(159.66,-.9),(160.33,-1.15),(160.78,0)],
        [(169.89,0),(170.30,-.8),(170.95,-1.05),(171.40,0)],
    ],
}

# Quiet harmonics answer the lead only in clear gaps. These use chord tones
# of the local Gb/Bb, Ebm9 and Ab6 voicings from the new arrangement.
Answers=(
    (107.55, .74, 'Verse breath',[(.070,77,.260,52),(.30,73,.250,46)]),
    (144.55, .53, 'Prechorus breath',[(.046,77,.218,50),(.226,78,.167,44)]),
    (159.53,1.22,'Final refrain response',[(.074,75,.390,57),(.514,72,.338,53)]),
)

def make_answer(label,duration,phrase):
    midi=song/'midi'/'shoegaze'/('Answer - '+label+'.mid')
    path=media/('Answer - '+label+'.wav')
    write_midi(midi,[(t/BEAT,p,d/BEAT,v) for t,p,d,v in phrase],0,1.14)
    with tempfile.TemporaryDirectory(dir=here) as temp:
        raw=Path(temp)/'dry.wav'
        subprocess.run(['fluidsynth','-ni','-C','0','-R','0','-g','.85','-T','wav',
                        '-O','float','-r',str(SR),'-F',str(raw),str(GUITAR),str(midi)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        guitar=filt(load(raw)[:round(duration*SR)],'bandpass',[310,4200])
    space=wet(guitar, 9, 7., .50)[:len(guitar)]
    sound=fade(guitar+.28*space,.024,.125)
    active=sound[round(.10*SR):round((duration-.13)*SR)]
    sound *= 10**(-33/20)/np.sqrt(np.mean(active**2))
    sf.write(path,sound,SR,'PCM_24')
    return path.name

def guid():
    return '{'+str(uuid4()).upper()+'}'

def envelope(points):
    return f'''    <VOLENV3
      EGUID {guid()}
      ACT 1 -1
      VIS 1 1 1
      LANEHEIGHT 0 0
      ARM 0
      DEFSHAPE 0 -1 -1
      VOLTYPE 1
{points}    >
'''

point_pattern=r'(?m)^      PT ([\d.]+) ([\d.]+) 0\n'
def automate(track, gestures):
    match=re.search(r'(?ms)^    <VOLENV3\n.*?^    >\n',track)
    existing=match[0] if match else ''
    old={float(t):float(g) for t,g in re.findall(point_pattern,existing)} or {0.:1.}
    knots=dict(old)
    for gesture in gestures:
        times,db=zip(*gesture)
        active={times[0],times[-1]}
        active.update(t for t in old if times[0]<=t<=times[-1])
        active.update(times)
        active.update(np.arange(times[0],times[-1],.06))
        for t in active:
            knots[t]=float(np.interp(t,list(old),list(old.values()))*10**(np.interp(t,times,db)/20))
    points=''.join(f'      PT {t:.9f} {g:.12f} 0\n' for t,g in sorted(knots.items()))
    if match:
        return track[:match.start()]+envelope(points)+track[match.end():]
    return track.replace('    <ITEM\n',envelope(points)+'    <ITEM\n',1)

def clips():
    result=f'''  <TRACK {guid()}
    NAME "Guitar answers"
    BEAT 0
    VOLPAN 1 0 -1 -1 1
    NCHAN 2
    MAINSEND 1 0
'''
    for i,(position,duration,label,phrase) in enumerate(Answers,7):
        name=make_answer(label,duration,phrase)
        result+=f'''    <ITEM
      POSITION {position:.9f}
      LENGTH {duration:.9f}
      LOOP 0
      FADEIN 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      IGUID {guid()}
      IID {i}
      NAME "{label}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      GUID {guid()}
      <SOURCE WAVE
        FILE "Media/{name}"
      >
    >
'''
    return result+'  >\n'

def stage(label,header,tracks,wave=True):
    def resolve(m):
        name=m[2]
        path=next(p/name for p in (media,session/'Media') if (p/name).is_file())
        return f'{m[1]}"{path}"'
    doc=header+''.join(tracks)+'>\n'
    doc=re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',resolve,doc)
    doc=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here/label}.{ "wav" if wave else "mp3"}"',doc)
    if wave:
        doc=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',doc)
        doc=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',doc)
        doc=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',doc)
    (here/(label+'.rpp')).write_text(doc)

header,*tracks=re.split(r'(?m)(?=^  <TRACK )',before.read_text())
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
revised=[]
for track in tracks:
    name=re.search(r'^    NAME "([^"]+)"',track,re.M)[1]
    revised.append(automate(track,Rides[name]) if name in Rides else track)
revised.append(clips())
(here/'Portable.rpp').write_text(header+''.join(revised)+'>\n')
stage('Premaster',header,revised)
stage('Backing',header,revised[2:])
stage('Guitars',header,[*revised[2:4],revised[-1]])
stage('Master',header,revised,wave=False)
