"""Make a short midrange pocket for Savage's last line."""
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from pedalboard import PeakFilter, Pedalboard
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
project = root / 'reaper/Blame Me for Everything'
session = 'Blame Me for Everything.rpp'
reference = here / 'Reference.rpp'
media = here / 'Media'
media.mkdir(exist_ok=True)
if not reference.exists():
    shutil.copy2(project/session,reference)
rpp = reference.read_text()
header,*tracks = re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, load

n = lambda t: round(float(t)*SR)
points = [(93.33,0),(93.46,.92),(93.61,1),(93.90,.91),(94.08,.39),
          (94.19,.24),(94.30,.78),(94.43,.77),(94.58,0)]
start, stop = n(points[0][0]), n(points[-1][0])
times = np.arange(start,stop)/SR
weight = np.interp(times,*np.array(points).T).astype(np.float32)[:,None]
weight[[0,-1]] = 0

for label,new_name,filters,side_weight in [
    ('Runaway | Instrumental','Runaway with last-line EQ.wav',[(505,-2.9,1.05),(1060,-3.8,.92)],.40),
    ('Veer | Guitar','Guitar with last-line EQ.wav',[(780,-5.0,.75)],.70),
]:
    i = next(i for i,t in enumerate(tracks) if f'    NAME "{label}"\n' in t)
    track = tracks[i]
    item = track.split('    <ITEM\n')[1]
    get = lambda name: re.search(rf'(?m)^      {name} (\S+)',item)[1]
    position,length,offset = [n(get(k)) for k in ('POSITION','LENGTH','SOFFS')]
    assert position<start<stop<position+length
    path = re.search(r'(?m)^        FILE "([^"]+)"',item)[1]
    data = load(project/path)
    a,b = offset+start-position,offset+stop-position
    pad = n(.13)
    original = data[a-pad:b+pad].copy()
    mid = original.mean(1,keepdims=True)
    work = mid+(original-mid)*side_weight
    eq = Pedalboard([PeakFilter(cutoff_frequency_hz=f,gain_db=g,q=q) for f,g,q in filters])
    delta = eq(work.T,SR).T-work
    data[a:b] += delta[pad:-pad]*weight
    sf.write(media/new_name,data,SR,'FLOAT')
    tracks[i] = track.replace(path,f'Media/{new_name}')

final = header + ''.join(tracks) + '>\n'
(here/session).write_text(final)
files = {p.name for p in media.glob('*.wav')}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda m:str((media if m[1] in files else project/'Media')/m[1]),final)
render = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
