"""Carry Farebi's bass pulse through the v1 turnaround gaps."""
from pathlib import Path
import re
from uuid import uuid4

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
beat = 60/85

def field(text, key):
    return re.search(rf'(?m)^      {key} (.*)$',text)[1]

def update(text, key, value):
    return re.sub(rf'(?m)^      {key} .*$',f'      {key} {value}',text)

def ride(track, points):
    block = re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',track)[0]
    old_times, old_levels = np.array(re.findall(r'^      PT (\S+) (\S+) 0$',block,re.M),float).T
    # Sample the overlapping gain curves densely so their product
    # remains linear enough through fast handoffs.
    times = sorted(set([*old_times,*[t for t,_ in points],
                        *np.arange(points[0][0],points[-1][0],.02)]))
    gains = np.interp(times,old_times,old_levels)
    offsets = np.interp(times,*np.asarray(points).T,left=0,right=0)
    amounts = gains*10**(offsets/20)
    head = re.sub(r'(?m)^      PT .*\n','',block).removesuffix('    >')
    after = head+''.join(f'      PT {t:.12f} {g:.12f} 0\n'
                         for t,g in zip(times,amounts))+'    >'
    return track.replace(block,after)

def carry_bass(track, position, length, bar_source, db, index):
    # Reuse the same stem and playback rate, from exactly one beat
    # earlier. This follows both the kick and the current E harmony.
    item = next(c for c in re.findall(r'(?ms)^    <ITEM\n.*?^    >$',track)
                if abs(float(field(c,'POSITION'))-bar_source)<1.e-7)
    rate = float(field(item,'PLAYRATE').split()[0])
    offset = float(field(item,'SOFFS')) + (position-beat-bar_source)*rate
    gain,*pan = field(item,'VOLPAN').split()
    new_gain = float(gain)*10**(db/20)
    for key,value in dict(POSITION=f'{position:.12f}', LENGTH=f'{length:.12f}',
                          SOFFS=f'{offset:.12f}', LOOP=0,
                          NAME='"Farebi | Bass continuation"',
                          IID=1600+index, GUID='{'+str(uuid4()).upper()+'}',
                          IGUID='{'+str(uuid4()).upper()+'}',
                          VOLPAN=' '.join([f'{new_gain:.12f}',*pan])).items():
        item = update(item,key,value)
    for key,t in [('FADEIN',.028),('FADEOUT',.055)]:
        value = field(item,key).split()
        value[1] = str(t)
        item = update(item,key,' '.join(value))
    return track.rstrip().removesuffix('>').rstrip()+'\n'+item+'\n  >\n'

for i,name in enumerate(('Drums','Bass','Music')):
    assert f'NAME "Farebi | {name}"' in tracks[i]
tracks[0] = ride(tracks[0],[
    (87.51,0),(87.86,.35),(88.15,1.05),(88.83,1.05),
    (89.05,1.8),(89.23,1.65),(89.46,.3),(89.59,0)])
tracks[0] = ride(tracks[0],[
    (166.59,0),(166.90,.75),(167.64,.75),(168.01,1.55),
    (168.19,1.6),(168.31,.7),(168.49,0)])
tracks[1] = carry_bass(tracks[1],88.928,.413,76.235294117647,-2.2,1)
tracks[1] = carry_bass(tracks[1],167.996,.436,155.294117647059,-2.0,2)
tracks[2] = ride(tracks[2],[
    (87.62,0),(87.94,.4),(88.17,.82),(89.32,.82),(89.56,.35),(89.77,0)])
tracks[2] = ride(tracks[2],[
    (166.64,0),(166.90,.62),(168.05,.85),(168.30,.47),(168.55,0)])

revised = header+''.join(tracks)
(stage/'Portable.rpp').write_text(revised)
for label,wav,text in [('Gained backing',True,header+''.join(tracks[:3])+'>\n'),
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
