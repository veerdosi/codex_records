"""Keep Farebi's low end centered and compensate the moving backing in v1."""
from pathlib import Path
import re
import numpy as np

stage = Path(__file__).resolve().parent
root = stage.parents[4]
title = 'Muh Pe Lovey Dovey v1'
project = root/'reaper'/title
baseline = stage/'Before.rpp'
if not baseline.exists():
    baseline.write_text((project/(title+'.rpp')).read_text())
original = baseline.read_text()
header,*tracks = re.split(r'(?m)(?=^  <TRACK )',original)
assert all(f'NAME "Farebi | {name}"' in track
           for name,track in zip(('Drums','Bass','Music'),tracks))
windows = [
    [(87.50,0),(87.72,.55),(88.13,.70),(88.24,2.15),(88.72,2.55),
     (88.88,1.85),(89.00,2.2),(89.23,2.6),(89.44,1.35),(89.60,.1),(89.78,0)],
    [(166.57,0),(166.8,.65),(166.96,1.8),(167.22,2.15),
     (167.58,2.3),(167.65,1.8),(167.94,2.25),(168.19,2.7),
     (168.32,2.2),(168.50,.65),(168.69,0)],
]
def ride(track, token, strength):
    envelope = re.search(rf'(?ms)^    <{token}\n.*?^    >$',track)[0]
    points = np.array(re.findall(r'^      PT (\S+) (\S+) 0$',envelope,re.M),float)
    times = list(points[:,0])
    for window in windows:
        times.extend(t for t,_ in window)
        times.extend(np.arange(window[0][0],window[-1][0],.02))
    times = np.unique(np.round(times,11))
    values = np.interp(times,*points.T)
    levels = sum(np.interp(times,*np.array(window).T,left=0,right=0) for window in windows)
    values *= 10**(levels*strength/20)
    new = re.sub(r'(?m)^      PT .*\n','',envelope).removesuffix('    >')
    new += ''.join(f'      PT {t:.12f} {g:.12f} 0\n' for t,g in zip(times,values))+'    >'
    return track.replace(envelope,new)

tracks[0]=ride(tracks[0],'VOLENV3',1)
tracks[2]=ride(tracks[2],'VOLENV3',.92)
# Bass notes are shared between the ears while the drums and
# melodic stem still make the hard left/right move.
tracks[1]=re.sub(r'(?ms)^    <PANENV2\n.*?^    >\n','',tracks[1])
tracks[1]=ride(tracks[1],'VOLENV3',.28)
revised=header+''.join(tracks)
(stage/'Portable.rpp').write_text(revised)
for label,wav,text in [('After backing',True,header+''.join(tracks[:3])+'>\n'),
                       ('Premaster',True,revised),('Master',False,revised)]:
    text=re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',
                lambda m:m[1]+f'"{project/"Media"/m[2]}"',text)
    ext='wav' if wav else 'mp3'
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
