"""Restore verse articulation and carry the native groove through two A bars."""
from fractions import Fraction
from pathlib import Path
from uuid import uuid4
import json
import re
import subprocess
import sys

import numpy as np
from pedalboard import HighShelfFilter, PeakFilter, Pedalboard, Reverb
from scipy.signal import correlate, correlation_lags, resample_poly, welch
import soundfile as sf

here=Path(__file__).resolve().parent
song=here.parents[1]
root=song.parents[2]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load, stretch

project=root/'reaper/Blame Me for Everything'
ref=here/'Reference.rpp'
rpp=ref.read_text() if ref.exists() else (project/'Blame Me for Everything.rpp').read_text()
ref.write_text(rpp)
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
media=here/'Media'
media.mkdir(exist_ok=True)
bar=240/87
beat=bar/4

def n(t):
    return round(t*SR)

def guid():
    return '{'+str(uuid4()).upper()+'}'

old_len=n(float(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)',header)[1]))
old_join=n(36*bar)
insert=n(bar)
new_join=old_join+insert
new_len=old_len+insert

def field(chunk,key):
    return n(float(re.search(rf'(?m)^      {key} (\S+)',chunk)[1]))

def clip(x,a,b):
    return x[n(a):n(b)].copy()

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def power(x):
    step=n(.15)
    return np.mean(x[:len(x)//step*step].reshape(-1,step,2)**2,axis=(1,2))

def active_db(x):
    p=power(x)
    return 10*np.log10(p[p>p.max()*.08].mean())

def level(x,target):
    return x*db(target-active_db(x))

def curve(x,points):
    t=np.arange(len(x))/SR
    return x*np.interp(t,*np.array(points).T).astype(np.float32)[:,None]

def read(chunk):
    a,b,offset=(field(chunk,k) for k in ('POSITION','LENGTH','SOFFS'))
    name=re.search(r'(?m)^        FILE "Media/([^"]+)"',chunk)[1]
    with sf.SoundFile(project/'Media'/name) as f:
        f.seek(offset)
        x=f.read(b,dtype='float32',always_2d=True)
    assert len(x)==b
    return a,x

def full(chunk):
    a,x=read(chunk)
    out=np.zeros((old_len,2),np.float32)
    out[a:a+len(x)]=x
    return out

def adjust_fields(chunk,position,length,offset):
    for key,val in [('POSITION',position),('LENGTH',length),('SOFFS',offset)]:
        chunk=re.sub(rf'(?m)^      {key} .*$',f'      {key} {val/SR:.12f}',chunk)
    return chunk

def shift(chunk):
    a,length,offset=(field(chunk,k) for k in ('POSITION','LENGTH','SOFFS'))
    if a>=old_join:
        return adjust_fields(chunk,a+insert,length,offset)
    if a+length<=old_join:
        return chunk
    prefix,item=chunk.split('    <ITEM\n',1)
    item='    <ITEM\n'+item.removesuffix('  >\n')
    before=old_join-a
    head=adjust_fields(item,a,before,offset)
    tail=adjust_fields(item,new_join,length-before,offset+before)
    tail=re.sub(r'(?m)^(      (?:IGUID|GUID) ).*$',lambda m:m[1]+guid(),tail)
    tail=re.sub(r'(?m)^      IID .*$',f'      IID {shift.iid}',tail)
    shift.iid+=1
    return prefix+head+tail+'  >\n'

shift.iid=40
def printed(chunk,x,file,position,name=None):
    sf.write(media/file,x,SR,'FLOAT')
    chunk=adjust_fields(chunk,position,len(x),0)
    chunk=re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',chunk)
    if name:
        chunk=re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m:m[1]+f'"{name}"',chunk)
    return chunk

# Recover the recorded cymbal and snare detail from the exact pre-EQ bed.
bed_at,bed=read(tracks[3])
bed=np.pad(bed,((0,insert),(0,0)))
a=old_join-bed_at
bed[a+insert:]=bed[a:-insert].copy()
bed[a:a+insert]=0
original_bed=load(project/'Media/Rebuild 01.wav')
dark_bed=load(here.parent/'intro_revision/Media/Runaway groove - verse EQ.wav')
assert original_bed.shape==dark_bed.shape
source_zero=11.033469387755+6*bar
fx=Pedalboard([PeakFilter(cutoff_frequency_hz=375,gain_db=-1.7,q=.75),
               HighShelfFilter(cutoff_frequency_hz=5500,gain_db=3.1,q=.69)])
start,end=63.8,35*bar
lo,hi=n(start)-bed_at,n(end)-bed_at
x=bed[lo:hi].copy()
delta=original_bed[n(start-source_zero):n(start-source_zero)+len(x)]-dark_bed[n(start-source_zero):n(start-source_zero)+len(x)]
detail=x+delta
bright=fx(detail.T,SR).T
bed[lo:hi]=x+curve(bright-x,[(0,0),(1.1,.72),(2.75,1),(end-start,1)])

# Let the original A bass and drum pattern play for both bars. Use the
# first E downbeat already aligned to Kanye in the preceding revision.
raw=load(song/'stems/runaway_bed_source_instrumental.wav')
a_start=n(35*bar)-bed_at
take=raw[n(253.20-214):n(253.20-214)+new_join-n(35*bar)]
take=fx(take.T,SR).T
take=level(take,active_db(bed[a_start-n(1.50):a_start])-.45)
take=curve(take,[(0,1),(1.8,1),(2*bar,.91)])
edge=n(.032)
bed[a_start:a_start+len(take)]=take
bed[a_start-edge:a_start]=fade(bed[a_start-edge:a_start],0,.032)
bed[a_start:a_start+edge]=fade(bed[a_start:a_start+edge],.032,0)
a_end=new_join-bed_at
bed[a_end-edge:a_end]=fade(bed[a_end-edge:a_end],0,.032)
bed[a_end:a_end+n(.015)]=fade(bed[a_end:a_end+n(.015)],.015,0)

# One contiguous separation pass keeps diction consistent across the verse.
# Preserve the original phrase window and reapply the saved light tuning.
sav_at,old_sav=read(tracks[5])
fresh=clip(load(here/'creepin lead.wav'),127.315-124.8,153.965-124.8)
fresh=stretch(fresh,len(old_sav)/SR,'sav_clear')
fresh=band(fresh,74,16300)
original_pitch=here.parent/'handoff_revision/pitch-map.txt'
pm=np.loadtxt(original_pitch)
pm[:,1]*=.80
np.savetxt(here/'pitch-map.txt',pm,fmt=['%d','%.6f'])
sf.write(here/'Fresh aligned.wav',fresh,SR,'FLOAT')
subprocess.run(['rubberband','-3','-F','--centre-focus','--pitchmap',str(here/'pitch-map.txt'),
    str(here/'Fresh aligned.wav'),str(here/'Fresh tuned.wav')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
tuned=load(here/'Fresh tuned.wav')
tuned=np.pad(tuned,((0,max(0,len(fresh)-len(tuned))),(0,0)))[:len(fresh)]
w=np.interp(np.arange(len(fresh)),pm[:,0],np.clip(abs(pm[:,1])*8,0,.88)).astype(np.float32)[:,None]
fresh=fresh+w*(tuned-fresh)
voc_fx=Pedalboard([PeakFilter(cutoff_frequency_hz=280,gain_db=-1.6,q=.8),
                   PeakFilter(cutoff_frequency_hz=4200,gain_db=2.15,q=.82),
                   HighShelfFilter(cutoff_frequency_hz=6500,gain_db=2.7,q=.72),
                   Reverb(room_size=.43,damping=.57,wet_level=.063,dry_level=.95,width=.78)])
clear=voc_fx(fresh.T,SR).T
target=active_db(band(old_sav,400,4900))
clear*=db(target-active_db(band(clear,400,4900)))
clear=fade(clear,.010,.10)

# Confirm the reference and the fresh vocal transients share their placement.
def lag_samples(x,y):
    d=correlate(x,y,method='fft')
    lags=correlation_lags(len(x),len(y))
    keep=abs(lags)<n(.043)
    return int(lags[keep][np.argmax(d[keep])])
old_h=band(old_sav,1200,7000).mean(1)
new_h=band(clear,1200,7000).mean(1)
lags=[]
for at in (1.0,4.5,8.0,11.0,15.0,18.0,22.0,25.0,28.0):
    s=slice(n(at),n(at+.66))
    lags.append(lag_samples(new_h[s],old_h[s]))
print('Median vocal alignment change',round(np.median(lags)*1000/SR,2),'ms',lags,flush=True)

# Answer the last word with a quieter version of the bookend piano phrase.
with sf.SoundFile(song/'sources/runaway.wav') as f:
    f.seek(n(.087));note=f.read(n(1.12),dtype='float32',always_2d=True)
note=fade(band(note,400,7600),.004,.15)
reply=np.zeros((insert*2+n(.42),2),np.float32)
for offset,pitch,gain in [(.70,76,-31.8),(2.20,71,-33.4),(4.12,68,-34.4),(6.56,76,-33.1)]:
    ratio=Fraction(2**((88-pitch)/12)).limit_denominator(110)
    hit=resample_poly(note,ratio.numerator,ratio.denominator,axis=0).astype(np.float32)
    hit=fade(hit[:n(1.11)],.008,.26)
    at=n(offset*beat)
    reply[at:at+len(hit)]+=level(hit,gain)
reply=Reverb(room_size=.51,damping=.58,wet_level=.17,dry_level=.90,width=.88)(reply.T,SR).T
reply=fade(reply,.006,.34)

template=tracks[1]
template=re.sub(r'\{[0-9A-F-]{36}\}',lambda _:guid(),template)
template=re.sub(r'(?m)^      IID .*$',f'      IID 78',template)
changed={
    3:printed(tracks[3],bed,'Runaway clear verse and handoff.wav',bed_at),
    5:printed(tracks[5],clear,'21 Savage clear lead.wav',sav_at,'21 Savage | Creepin, restored lead')
}
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {new_len/SR:.12f} 0 1000',header)
def marker(m):
    at=n(float(m[2]))
    if at>=old_join:
        at+=insert
    return f'{m[1]}{at/SR:.10f}{m[3]}'
header=re.sub(r'(?m)^(  MARKER \d+ )(\S+)( ".*)$',marker,header)
header=header.replace('Native A-to-E turnaround','Two-bar A-to-E turnaround')
final=header+''.join(changed[i] if i in changed else shift(chunk) for i,chunk in enumerate(tracks))
final+=printed(template,reply,'Piano handoff reply.wav',n(35*bar),'Veer | Piano reply into Kanye')+'>\n'
(here/'Blame Me for Everything.rpp').write_text(final)
new_files={p.name for p in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',lambda m:str((media if m[1] in new_files else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
def spectrum(x):
    f,p=welch(x,SR,nperseg=2048,axis=0)
    values=[10*np.log10(np.sum(p[(f>=a)&(f<b)])) for a,b in ((250,1000),(1000,3500),(3500,7000),(7000,14500))]
    return [round(v-values[1],2) for v in values]
comparison={'vocal_before':spectrum(old_sav),'vocal_after':spectrum(clear),
            'backing_before':spectrum(read(tracks[3])[1][n(67)-bed_at:n(94)-bed_at]),
            'backing_after':spectrum(bed[n(67)-bed_at:n(94)-bed_at]),
            'end_handoff':round(new_join/SR,3),'duration':round(new_len/SR,3)}
(here/'clarity-check.json').write_text(json.dumps(comparison,indent=2)+'\n')
print(json.dumps(comparison),flush=True)
