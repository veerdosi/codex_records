"""Rebalance the song from time-aligned vocal and instrumental tracks."""
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

import numpy as np
from scipy.signal import butter, sosfilt
import soundfile as sf

here = Path(__file__).resolve().parent
song = here.parents[1]
root = song.parents[2]
media = root/'reaper/When You Leave/Media'
sr = 44100
duration = 168.3810344828
length = round(sr*duration)
sections = [
    ('First hook',24.8,46.66,8),
    ('21 Savage verse',53.8,88.15,3),
    ('Kanye verse',92.25,113.55,8),
    ('Kanye build',114.0,135.68,8),
    ('Final hook',135.85,157.45,8),
]
original = (here/'Original.rpp').read_text()
header,*chunks = re.split(r'(?m)(?=^  <TRACK )',original)
chunks[-1] = chunks[-1].rstrip().removesuffix('>').rstrip()+'\n'


def filtered(x, band):
    return sosfilt(butter(2,band,fs=sr,btype='bandpass',output='sos'),x,axis=0)


def read(path):
    audio,rate = sf.read(path,dtype='float32',always_2d=True)
    assert rate==sr, path
    return audio


def array(chunk):
    name = re.search(r'(?m)^\s+FILE "Media/(.*)"',chunk)[1]
    at = round(float(re.search(r'(?m)^      POSITION (\S+)',chunk)[1])*sr)
    audio = read(media/name)
    assert 0<=at<length and at+len(audio)<=length+1
    x = np.zeros((length,2),dtype='float32')
    end = min(length,at+len(audio))
    x[at:end] = audio[:end-at]
    return at,audio,x


def levels(vocal, bed):
    def power(audio):
        step=round(.20*sr)
        windowed=audio[:len(audio)//step*step].reshape(-1,step,2)
        return np.mean(windowed**2,axis=(1,2))
    presence = power(filtered(vocal,(400,4900)))
    gate = presence>presence.max()*.075
    values=[]
    for band in ((58,12500),(400,4900)):
        vox,inst=[power(filtered(track,band)) for track in (vocal,bed)]
        v,b=[10*np.log10(max(1e-12,x[gate].mean())) for x in (vox,inst)]
        values.append((v,b,v-b))
    return values


def report(tracks, label):
    print(label,'voice / backing / difference, broadband and presence',flush=True)
    combined=sum(tracks.values())
    for name,start,end,index in sections:
        s=slice(round(start*sr),round(end*sr))
        voice=tracks[index][s]
        band=combined[s]-voice
        print(name,[[round(v,2) for v in values] for values in levels(voice,band)],flush=True)


tracks={}
for i,chunk in enumerate(chunks,1):
    at,clip,x=array(chunk)
    tracks[i]=x
    if i==1:
        src_at,source=at,clip

metadata=json.loads((here/'sections.json').read_text())
assert metadata['track_position_samples']==src_at
packed=read(here/'Kanye lead.wav')
lead=np.zeros_like(source)
start=0
for a,b in metadata['frame_ranges']:
    assert start+b-a<=len(packed)+1
    part=packed[start:start+b-a].copy()
    part=filtered(part,(77,12300)).astype('float32')
    # Remove model tails in the silent padding between excerpts.
    part[:441] *= np.linspace(0,1,441)[:,None]
    part[-441:] *= np.linspace(1,0,441)[:,None]
    lead[a:b]=part
    start+=b-a+metadata['padding']
assert np.max(np.abs(lead))<1.8
tracks[8]=np.zeros_like(tracks[1])
tracks[8][src_at:src_at+len(lead)]=lead
tracks[1]-=tracks[8]
original_pcm=read(song/'analysis/Premaster.wav')
assert np.max(np.abs(sum(tracks.values())-original_pcm))<2e-5
report(tracks,'Before')
if '--measure' in sys.argv:
    sys.exit(0)

points=json.loads((here/'gains.json').read_text())
points={int(track):values for track,values in points.items()}


def amplitude(db):
    return 10**(db/20)


def volume_envelope(chunk, values):
    points=''.join(f'      PT {t:.7f} {amplitude(db):.11f} 0\n' for t,db in values)
    new=('    <VOLENV3\n'
         f'      EGUID {{{str(uuid4()).upper()}}}\n'
         '      ACT 1 -1\n      VIS 1 1 1\n      LANEHEIGHT 0 0\n'
         '      ARM 0\n      DEFSHAPE 0 -1 -1\n      VOLTYPE 1\n'+points+'    >\n')
    assert '    <VOLENV3' not in chunk
    return chunk.replace('    <ITEM\n',new+'    <ITEM\n',1)


def retarget(chunk, name, file):
    chunk = re.sub(r'(?m)^(    +NAME )".*"$',lambda m:m[1]+f'"{name}"',chunk)
    return chunk.replace('FILE "Media/Track 01.wav"',f'FILE "Media/{file}"')


new_lead=retarget(chunks[0],'Kanye West | Lead vocal','Kanye lead.wav')
new_lead=re.sub(r'\{[0-9A-F-]{36}\}',lambda _:'{'+str(uuid4()).upper()+'}',new_lead)
new_lead=new_lead.replace('      IID 1\n','      IID 8\n')
chunks[0]=retarget(chunks[0],'Runaway | Instrumental','Runaway instrumental.wav')
chunks.append(new_lead)
for track,values in points.items():
    x=tracks[track]
    t,g=np.array(values).T
    curve=np.interp(np.arange(len(x))/sr,t,amplitude(g)).astype('float32')
    x*=curve[:,None]
    chunks[track-1]=volume_envelope(chunks[track-1],values)
report(tracks,'After')

staging=here/'Media'
staging.mkdir(exist_ok=True)
sf.write(staging/'Runaway instrumental.wav',source-lead,sr,'FLOAT')
sf.write(staging/'Kanye lead.wav',lead,sr,'FLOAT')
rpp=header+''.join(chunks)+'>\n'
(here/'When You Leave.rpp').write_text(rpp)
sf.write(here/'Premaster balanced.wav',sum(tracks.values()),sr,'FLOAT')
def relative_media(m):
    file=m[1]
    path=staging/file if file in ('Runaway instrumental.wav','Kanye lead.wav') else media/file
    assert path.is_file()
    return f'FILE "{path}"'
render=re.sub(r'(?m)(?<=\s)FILE "Media/([^"]+)"',relative_media,rpp)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master balanced.mp3"',render)
(here/'Render.rpp').write_text(render)
