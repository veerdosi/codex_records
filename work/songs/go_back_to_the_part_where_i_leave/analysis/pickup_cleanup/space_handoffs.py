"""Add two beats of instrumental space before each returning verse."""
from pathlib import Path
from itertools import count
import json
import re
import sys
from uuid import uuid4

import numpy as np
from pedalboard import HighShelfFilter, PeakFilter
from scipy import signal
import soundfile as sf

stage=Path(__file__).resolve().parent
root=stage.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR,db,load

old_info=json.loads((stage.parent/'transition_remaster/revision.json').read_text())
project=root/'reaper/Go Back to the Part Where I Leave'
rpp=(stage/'Trimmed.rpp').read_text()
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
n=lambda t:round(float(t)*SR)
sec=lambda a:f'{a/SR:.12f}'
step=n(120/87)
first=n(old_info['eminem_bar'])
second=n(old_info['kanye_return'])
duration=n(old_info['duration'])+2*step
filename='Runaway - extended handoffs.wav'
bed_origin=n(16.551088435374)

def level(x):
    return float(10*np.log10(np.mean(x*x)+1e-12))

def band(x,lo,hi):
    return signal.sosfilt(signal.butter(2,[lo,hi],btype='bandpass',fs=SR,output='sos'),x,axis=0)

def ride(x, points):
    return np.interp(np.arange(len(x)),*np.asarray(points).T).astype(np.float32)[:,None]

def fade(size):
    return (.5-.5*np.cos(np.linspace(0,np.pi,size,dtype=np.float32)))[:,None]

def bell(x,hz,gain,q):
    return PeakFilter(cutoff_frequency_hz=hz,gain_db=gain,q=q)(x.T,SR).T

def shelf(x,hz,gain):
    return HighShelfFilter(cutoff_frequency_hz=hz,gain_db=gain,q=.70)(x.T,SR).T

def label(chunk):
    return re.search(r'^    NAME "([^"]+)"',chunk,re.M)[1]

def field(item,key):
    return re.search(rf'^      {key} (\S+)',item,re.M)[1]

def edit(item,key,value):
    return re.sub(rf'(?m)^      {key} .*$',f'      {key} {value}',item)

old=load(project/'Media/Runaway - continuous groove.wav')
first_i,second_i=first-bed_origin,second-bed_origin
raw=load(root/'work/songs/blame_me_for_everything/stems/runaway_bed_source_instrumental.wav')

# Follow the source C# bass into the extra two beats. Keep its exact
# timing and use the processing from the outgoing Runaway passage.
before=n(.68)
source_i=n(214.58-214)+first-n(22*240/87)
extension=raw[source_i-before:source_i+step].copy()
extension=bell(shelf(extension,2200,2.2),1060,1.25,.76)
x=extension[:n(.40)]
y=old[first_i-before:first_i-before+len(x)]
x=band(x,55,2800); y=band(y,55,2800)
scale=float(np.sum(x*y)/np.sum(x*x))
assert .2<scale<.85 and np.corrcoef(x.ravel(),y.ravel())[0,1]>.90
extension*=scale
blend=fade(n(.10))
i=first_i-n(.31)
patch_start=before-n(.31)
old[i:i+len(blend)]=old[i:i+len(blend)]*(1-blend)+extension[patch_start:patch_start+len(blend)]*blend
old[i+len(blend):first_i]=extension[patch_start+len(blend):before]
first_extra=extension[before:]

# Bring the returning E harmony forward. This two-beat pickup is from
# the same Runaway kit and chord, starting on beat three of an E bar.
echo_at=n(30*240/87)+step-bed_origin
second_extra=old[echo_at:echo_at+step].copy()
second_extra=bell(second_extra,1030,1.0,.77)
second_extra*=db(.15+level(old[second_i-step:second_i])-level(second_extra))
# Take some body out of the last chord while opening the next backing
# in the same band. Keep a steady kick and a gradual change in color.
left=old[second_i-n(3.0):second_i]
filtered=bell(left,920,-1.60,.76)
left+=(filtered-left)*ride(left,[(0,0),(n(1.9),.70),(len(left)-1,1)])

right=old[second_i:second_i+n(46)]
filtered=shelf(bell(right,1020,1.75,.76),2700,.68)
right+=(filtered-right)*ride(right,[(0,.92),(n(.40),1),(n(39),1),(len(right)-1,0)])
# End one drum tail and bring the next in before its downbeat. The
# splice itself retains the first transient at each grid anchor.
edge=n(.024)
for extra,index,preroll in [
    (first_extra,first_i,raw[n(214.58-214)-edge:n(214.58-214)]*scale),
    (second_extra,second_i,old[echo_at+step:echo_at+step+edge])]:
    extra[-edge:]=extra[-edge:]*(1-fade(edge))+preroll*fade(edge)*.88

edge2=n(.068)
pre=old[echo_at-edge2:echo_at].copy()
w=fade(edge2)
old[second_i-edge2:second_i]=old[second_i-edge2:second_i]*(1-w)+pre*w

bed=np.concatenate((old[:first_i],first_extra,old[first_i:second_i],second_extra,old[second_i:]))
assert len(bed)==len(old)+2*step and np.isfinite(bed).all()
sf.write(stage/'Media'/filename,bed,SR,'FLOAT')

def shift(pos):
    return step*(int(pos>=first)+int(pos>=second))

new_iids=count(261)

def unique(item):
    item=re.sub(r'(?m)^(      (?:GUID|IGUID) ).*$',lambda m:m[1]+'{'+str(uuid4()).upper()+'}',item)
    return edit(item,'IID',str(next(new_iids)))

def move_track(chunk):
    title=label(chunk)
    pre,*items=re.split(r'(?m)(?=^    <ITEM\n)',chunk)
    if not items:
        return chunk
    close='  >\n'
    assert items[-1].endswith(close)
    items[-1]=items[-1].removesuffix(close)
    output=[pre]
    for item in items:
        pos,length,off=[n(field(item,k)) for k in ('POSITION','LENGTH','SOFFS')]
        if title=='Runaway | Instrumental':
            assert pos==bed_origin
            item=edit(item,'LENGTH',sec(len(bed)))
            item=re.sub(r'(?m)(?<=FILE ")[^"]+',str(stage/'Media'/filename),item)
            output.append(item)
        elif title=='Eminem | Love the Way You Lie':
            # The item has silence at the head and starts 57 ms before its bar.
            output.append(edit(item,'POSITION',sec(pos+step)))
        elif title=='Veer | Three record rewinds':
            # The last room tail rings into the new two-beat gap.
            output.append(edit(item,'POSITION',sec(pos+step)))
        else:
            boundaries=[pos,*[t for t in (first,second) if pos<t<pos+length],pos+length]
            for i,(a,b) in enumerate(zip(boundaries,boundaries[1:])):
                part=edit(edit(edit(item,'POSITION',sec(a+shift(a))),'LENGTH',sec(b-a)),
                          'SOFFS',sec(off+a-pos))
                output.append(unique(part) if i else part)
    return ''.join(output)+close

header=re.sub(r'(?m)^(  MARKER \d+ )(\S+)( .*)$',
              lambda m:f'{m[1]}{sec(n(m[2])+shift(n(m[2])))}{m[3]}',header)
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {sec(duration)} 0 1000',header)
(stage/'Spaced handoffs.rpp').write_text(header+''.join(move_track(x) for x in tracks)+'>\n')
out={'gaps':[[first/SR,(first+step)/SR],[(second+step)/SR,(second+2*step)/SR]],
     'duration':duration/SR,'eminem_bar':(first+step)/SR,'kanye_bar':(second+2*step)/SR}
(stage/'spaced_grid.json').write_text(json.dumps(out,indent=2)+'\n')
print(out)
