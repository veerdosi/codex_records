"""Reduce the first handoff to one phrase over the recorded E pedal."""
from pathlib import Path
from uuid import uuid4
import re
import sys

import numpy as np
from pedalboard import Reverb
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR,db,fade,filt,load

project=root/'reaper/Blame Me for Everything'
name='Blame Me for Everything.rpp'
source=here/'Rim pickup.rpp'
media=here/'Media'
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',source.read_text())
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
beat=60/87
n=lambda t:round(t*SR)
start=n(88*beat)
cut=n(65.81)
guid=lambda:'{'+str(uuid4()).upper()+'}'

def name_of(chunk):
    return re.search(r'(?m)^    NAME "([^"]+)"',chunk)[1]

layers={'Veer | Guitar','Veer | Strings','Veer | Keys','Veer | Upright transition phrases',
        'Veer | Cello transition phrases','Veer | Transition echoes and room'}
points=[(0,1),(60.20,1),(60.68,0),(67.92,0),(68.55,1)]
for i,t in enumerate(tracks):
    if name_of(t) not in layers:
        continue
    assert '<VOLENV3' not in t
    env='    <VOLENV3\n'+f'      EGUID {guid()}\n'
    env+='      ACT 1 -1\n      VIS 1 1 1\n      LANEHEIGHT 0 0\n      ARM 0\n      DEFSHAPE 0 -1 -1\n      VOLTYPE 1\n'
    env+=''.join(f'      PT {at:.8f} {gain} 0\n' for at,gain in points)+'    >\n'
    tracks[i]=t.replace('    <ITEM\n',env+'    <ITEM\n',1)

piano=load(here/'Upright answer raw.wav')[:cut-start]
piano=np.pad(piano,((0,max(0,cut-start-len(piano))),(0,0)))
piano=filt(filt(piano,'highpass',145),'lowpass',8900)
piano=Reverb(room_size=.37,damping=.61,wet_level=.14,dry_level=.92,width=.82)(piano.T,SR).T
step=n(.1)
p=(piano[:len(piano)//step*step].reshape(-1,step,2)**2).mean((1,2))
piano*=db(-25.5-10*np.log10(p[p>p.max()*.08].mean()))
piano=fade(piano,.015,.35)
file='Upright answer before Savage.wav'
sf.write(media/file,piano,SR,'FLOAT')
chunk=next(x for x in tracks if name_of(x)=='Veer | Handoff Nylon guitar')
chunk=re.sub(r'\{[0-9A-F-]{36}\}',lambda _:guid(),chunk)
chunk=re.sub(r'(?m)^      IID .*$', '      IID 120',chunk)
chunk=re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m:m[1]+'"Veer | Upright answer before Savage"',chunk)
for key,value in [('POSITION',start),('LENGTH',len(piano)),('SOFFS',0)]:
    chunk=re.sub(rf'(?m)^      {key} .*$',f'      {key} {value/SR:.12f}',chunk)
chunk=re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)
final=header+''.join(tracks)+chunk+'>\n'
final=final.replace('"Guitar answers"','"Upright answer into Savage"')
(here/name).write_text(final)
files={p.name for p in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',lambda m:str((media if m[1] in files else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
print('Single piano phrase',round(start/SR,4),round((start+len(piano))/SR,4),
      'Savage item starts at 66.0265',flush=True)
