"""Keep the multitrack arrangement and separate the approved final section's dry and wet prints."""
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

import numpy as np
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
project = root / 'reaper/Blame Me for Everything'
name = 'Blame Me for Everything.rpp'
media = here / 'Media'
media.mkdir(exist_ok=True)
sys.path.insert(0, str(root/'work/shared'))
from dsp import SR, fade, load

n = lambda seconds: round(float(seconds)*SR)
def seconds(frames):
    return f'{frames/SR:.12f}'

details = json.loads((here/'edit-check.json').read_text())
chorus = n(details['slowdown_starts'])
outro = n(details['outro_starts'])
head = n(.12)
join = chorus-head
mix = load(here/'Slow and Reverbed premaster.wav')
source = load(here/'Final section source.wav')
stretched = load(here/'Final section stretched.wav')
target = np.loadtxt(here/'Time map.txt',dtype=int)[-1,1]
dry = np.pad(stretched,((0,max(0,target-len(stretched))),(0,0)))[:target]
blend = n(.056)
dry[:blend] = fade(source[:blend],0,blend/SR)+fade(dry[:blend],blend/SR,0)
wet = mix[join:].copy()
wet[:len(dry)] -= dry
assert np.max(abs(wet[:blend]))<2e-6
assert len(wet)==len(mix)-join
sf.write(media/'Final chorus and outro - slowed.wav',dry,SR,'FLOAT')
sf.write(media/'Final chorus and outro - reverb.wav',wet,SR,'FLOAT')

reference = (here/'Reference.rpp').read_text()
header,*tracks = re.split(r'(?m)(?=^  <TRACK )',reference)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
template = next(t for t in tracks if '    NAME "Runaway | Instrumental"' in t)
assert template.count('    <ITEM\n')==1
trimmed=[]
for t in tracks:
    prefix,*items = re.split(r'(?m)(?=^    <ITEM\n)',t.removesuffix('  >\n'))
    before=[]
    for item in items:
        pos=n(re.search(r'(?m)^      POSITION (\S+)',item)[1])
        length=n(re.search(r'(?m)^      LENGTH (\S+)',item)[1])
        if pos>=join:
            continue
        if pos+length>join:
            item=re.sub(r'(?m)^      LENGTH .*$',f'      LENGTH {seconds(join-pos)}',item)
        before.append(item)
    if before:
        trimmed.append(prefix+''.join(before)+'  >\n')

for iid,label,filename,audio in [
    (123,'Final chorus and outro | Slowed','Final chorus and outro - slowed.wav',dry),
    (124,'Final chorus and outro | Reverb','Final chorus and outro - reverb.wav',wet),
]:
    t=re.sub(r'\{[0-9A-F-]{36}\}',lambda _: '{'+str(uuid4()).upper()+'}',template)
    t=re.sub(r'(?m)^(    +NAME )"[^"]+"$',lambda m:m[1]+f'"{label}"',t)
    for k,v in [('POSITION',seconds(join)),('LENGTH',seconds(len(audio))),('SOFFS',0),('IID',iid)]:
        t=re.sub(rf'(?m)^      {k} .*$',f'      {k} {v}',t)
    t=re.sub(r'(?m)^        FILE .*$',f'        FILE "Media/{filename}"',t)
    trimmed.append(t)

header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {seconds(len(mix))} 0 1000',header)
header=re.sub(r'(?m)^(  MARKER 12 )\S+',lambda m:m[1]+seconds(outro),header)
# Keep the REAPER bar grid aligned to the five printed tempo anchors.
mapping=np.loadtxt(here/'Time map.txt',dtype=int)[1:6,1]
assert mapping[0]==head and len(mapping)==5
tempo_lines=[]
for index,at in enumerate(mapping):
    bpm=60*SR/(mapping[index+1]-at) if index<4 else details['final_tempo']
    tempo_lines.append(f'    PT {seconds(join+at)} {bpm:.10f} 1 0 0 1\n')
last_tempo='    PT 0.0000000000 87 1 262148 0 1\n'
assert last_tempo in header
header=header.replace(last_tempo,last_tempo+''.join(tempo_lines))
final=header+''.join(trimmed)+'>\n'
(here/name).write_text(final)
names={p.name for p in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((media if m[1] in names else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Session check.mp3"',render)
(here/'Session check.rpp').write_text(render)
print('Editable session assembled with separate dry and reverb prints.')
