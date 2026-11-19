"""Restore the native stereo field and level both turnarounds."""
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
pan = re.compile(r'(?ms)^    <PANENV2\n.*?^    >\n')
assert len(pan.findall(original))==6
for i,track in enumerate(tracks):
    if pan.search(track):
        block=pan.search(track)[0]
        points = np.array(re.findall(r'^      PT (\S+) (\S+) 0$',block,re.M),float)
        assert len(points)==13 and np.all((points[1:,0]>88)&(points[1:,0]<169)),points
        tracks[i]=pan.sub('',track)

windows=[
    [(87.62,0),(87.95,.22),(88.22,.05),(88.49,-.25),(88.70,-.90),(88.95,-.86),
     (89.15,-.43),(89.30,-.16),(89.44,-.40),(89.62,0)],
    [(166.65,0),(166.89,.5),(167.19,.82),(167.56,.82),
     (168.04,1.15),(168.18,1.55),(168.32,1.34),(168.53,0)],
]
def ride(track,amount):
    env=re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',track)[0]
    old=np.array(re.findall(r'^      PT (\S+) (\S+) 0$',env,re.M),float)
    first=[t for points in windows for t,_ in points]
    dense=np.concatenate([np.arange(points[0][0],points[-1][0],.05) for points in windows])
    times=np.unique(np.round(np.r_[old[:,0],first,dense],10))
    gains=np.interp(times,*old.T)
    adjustment=sum(np.interp(times,*np.array(points).T,left=0,right=0) for points in windows)
    gains*=10**(amount*adjustment/20)
    prefix=re.sub(r'^      PT .*\n','',env,flags=re.M).removesuffix('    >')
    new=''.join(f'      PT {t:.12f} {g:.12f} 0\n' for t,g in zip(times,gains))
    return track.replace(env,prefix+new+'    >')

for i,weight in enumerate((1,.58,1)):
    tracks[i]=ride(tracks[i],weight)
revised=header+''.join(tracks)
(stage/'Portable.rpp').write_text(revised)
for label,wav in [('Premaster',True),('Master',False)]:
    text=re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',
                lambda m:m[1]+f'"{project/"Media"/m[2]}"',revised)
    ext='wav' if wav else 'mp3'
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/(label + " balanced")}.{ext}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
