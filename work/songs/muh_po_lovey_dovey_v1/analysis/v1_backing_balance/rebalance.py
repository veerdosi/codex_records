"""Restore the instrumental support in the 85 BPM piano-free mix."""
from pathlib import Path
import math
import re
from uuid import uuid4

stage = Path(__file__).resolve().parent
root = stage.parents[4]
title = 'Muh Pe Lovey Dovey v1'
project = root/'reaper'/title
baseline = stage/'Before.rpp'
if not baseline.exists():
    baseline.write_text((project/(title+'.rpp')).read_text())
original = baseline.read_text()
item_pattern = re.compile(r'(?ms)^    <ITEM\n.*?^    >$')
header, *tracks = re.split(r'(?m)(?=^  <TRACK )',original)
beat = 60/85
old_end = 206.117647058824

def item_field(item,key):
    return re.search(rf'(?m)^      {key} (.*)$',item)[1]

def set_field(item,key,content):
    return re.sub(rf'(?m)^      {key} .*$',f'      {key} {content}',item)

def item_gain(item, relative_db):
    g,*rest = item_field(item,'VOLPAN').split()
    return set_field(item,'VOLPAN',' '.join([f'{float(g)*10**(relative_db/20):.12f}',*rest]))

def envelope(track,points):
    env = re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',track)[0]
    values = [(0,0),*points,(old_end,0)]
    segment = ''.join(f'      PT {t:.12f} {10**(gain/20):.12f} 0\n' for t,gain in values)
    replaced = re.sub(r'(?m)^      PT .*\n','',env)
    return track.replace(env,replaced.removesuffix('    >')+segment+'    >')

def find_item(track,time):
    return next(item for item in item_pattern.findall(track)
                if math.isclose(float(item_field(item,'POSITION')),time,abs_tol=1.e-7))

def with_clip(track,source_item,position,length,offset,gain,fade_in,fade_out,label):
    item = source_item
    changes=dict(POSITION=position,LENGTH=length,SOFFS=offset,
                 GUID='{'+str(uuid4()).upper()+'}',IGUID='{'+str(uuid4()).upper()+'}',
                 NAME=f'"{label}"',IID=950+round(position))
    for k,v in changes.items():
        item=set_field(item,k,v)
    for k,v in [('FADEIN',fade_in),('FADEOUT',fade_out)]:
        prev=item_field(item,k).split()
        prev[1]=str(v)
        item=set_field(item,k,' '.join(prev))
    item=item_gain(item,gain)
    return track.rstrip().removesuffix('>').rstrip()+'\n'+item+'\n  >\n'

encore=[(88.00,0),(88.17,1.4),(89.56,1.4),(89.72,.55),(90.15,0)]
calm=[(166.64,0),(166.90,1.75),(168.3,1.75),(168.47,.9),(168.9,0)]
calm_pickup=[(169.80,0),(170.78,1.3),(171.70,1.8),(172.04,.65),(172.34,0)]
drums,bass,music=tracks[:3]
assert all(f'NAME "Farebi | {name}"' in tr
           for name,tr in zip(('Drums','Bass','Music'),(drums,bass,music)))
drums=envelope(drums,encore+calm+calm_pickup)
# Ease out of the final bass pickup. Leave the arrangement's own
# gaps between bass notes and its real change into the chorus.
bass=envelope(bass,encore+calm+[(169.1,.05),(169.74,.12),
    (170.46,-.9),(170.87,-1.1),(171.82,-1.1),(172.26,0)])
music=envelope(music,[(88.01,0),(88.18,1.3),(89.57,1.3),(89.82,0),
    (91.78,0),(91.94,2.7),(92.98,2.7),(93.26,0),
    (166.66,0),(166.93,1.75),(168.29,1.75),(168.62,0),
    (169.75,0),(170.82,2.1),(171.84,2.7),(172.37,0)])
# Use the kit one bar earlier as a quiet rhythmic bed below the
# bare hook pickup, at the same bar phase as the omitted drums.
source=find_item(drums,76.235294117647)
clip_at=92.0- .4*beat
ref=clip_at-4*beat
offset=float(item_field(source,'SOFFS'))+(ref-float(item_field(source,'POSITION')))*17/18
drums=with_clip(drums,source,clip_at,93.114-clip_at,offset,-7.5,.11,.16,
                'Farebi kit | Encore turnaround')
# Carry the coda kit into the start of the next bar and taper it
# beneath the existing plucks and chord instead of dropping it flat.
coda_start=200.470588235294
break_at=coda_start+4*beat
source=find_item(drums,coda_start)
drums=drums.replace(source,item_gain(source,2.1))
drums=with_clip(drums,source,break_at,2.30*beat,float(item_field(source,'SOFFS')),
                -1.7,.017,.92,'Farebi kit | Coda tail')
for position,gain in [(coda_start,1.5),(break_at,3.0)]:
    source=find_item(music,position)
    music=music.replace(source,item_gain(source,gain))
tracks[:3]=drums,bass,music
revised=header+''.join(tracks)
(stage/'Portable.rpp').write_text(revised)

def stage_project(text,label,wav,backing=False):
    if backing:
        head,*arrangement=re.split(r'(?m)(?=^  <TRACK )',text)
        text=head+''.join(arrangement[:3])+'>\n'
    text=re.sub(r'FILE "Media/([^"]+)"',lambda m:f'FILE "{project/"Media"/m[1]}"',text)
    suffix='wav' if wav else 'mp3'
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{suffix}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)

stage_project(original,'Before backing',True,backing=True)
stage_project(revised,'After backing',True,backing=True)
stage_project(revised,'Premaster',True)
stage_project(revised,'Master',False)
