"""Fit a replacement performance to the approved Runaway arrangement."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

import numpy as np
from pedalboard import PeakFilter, Pedalboard, Reverb
from scipy.ndimage import gaussian_filter1d
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[4]
project=root/'reaper/Blame Me for Everything'
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load, stretch


@dataclass(frozen=True)
class Performance:
    file: str
    title: str
    performer: str
    excerpt: float
    start: float
    stop: float
    source_downbeat: float
    tempo: float


takes={
    'eminem':Performance('love_the_way_you_lie','Love the Way You Lie','Eminem',16.5,23.43,53.64,23.48659,86.96691),
    'savage':Performance('dark_days','dark days','21 Savage',19.0,22.14,51.62,21.17011,82.55840),
    'loyalty':Performance('said_n_done','Said N Done','21 Savage',9.5,11.24,41.74,12.06786,80.17180),
}
mode=sys.argv[1]
take=takes[mode]
stage=here/mode
media=stage/'Media'
media.mkdir(parents=True,exist_ok=True)
rpp=(project/'Blame Me for Everything.rpp').read_text()
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',rpp)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
n=lambda t:round(float(t)*SR)

def first(pattern,chunk):
    return re.search(pattern,chunk,re.M)[1]
def name(track):
    return first(r'^    NAME "([^"]+)"',track)
def field(track,k):
    return first(rf'^      {k} (\S+)',track)
def set_field(chunk,k,v):
    return re.sub(rf'(?m)^      {k} .*$',f'      {k} {v}',chunk)
def media_path(track):
    return first(r'^        FILE "([^"]+)"',track)
def seconds(x):
    return f'{x/SR:.12f}'
def rms(x):
    return float(10*np.log10(max(np.mean(x*x),1e-12)))
def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)
def blocks(x,dt=.025):
    step=n(dt)
    padded=np.pad(x,((0,-len(x)%step),(0,0)))
    return np.mean(padded.reshape(-1,step,2)**2,axis=(1,2))
def active(x):
    p=blocks(band(x,190,6300),.085)
    return float(10*np.log10(np.mean(p[p>p.max()*.08])))
def print_media(i,x,filename):
    path=media_path(tracks[i])
    sf.write(media/filename,x,SR,'FLOAT')
    tracks[i]=tracks[i].replace(path,f'Media/{filename}')

voice_index=next(i for i,t in enumerate(tracks) if name(t).startswith('21 Savage |'))
bed_index=next(i for i,t in enumerate(tracks) if name(t)=='Runaway | Instrumental')
verse=n(first(r'^  MARKER 6 (\S+)',header))
lift=n(first(r'^  MARKER 7 (\S+)',header))
old=load(project/media_path(tracks[voice_index]))
raw=load(here/f'{take.file} lead.wav')
assert take.stop-take.excerpt<len(raw)/SR
x=raw[n(take.start-take.excerpt):n(take.stop-take.excerpt)].copy()
ratio=take.tempo/87
at=verse+n((take.start-take.source_downbeat)*ratio)
if abs(ratio-1)>.002:
    x=stretch(x,len(x)*ratio/SR,mode+' fit')
assert at+len(x)<lift
dry=band(x,73,15500)
if mode=='eminem':
    chain=Pedalboard([PeakFilter(cutoff_frequency_hz=280,gain_db=-.75,q=.87),
                     PeakFilter(cutoff_frequency_hz=3800,gain_db=-.7,q=.88)])
else:
    chain=Pedalboard([PeakFilter(cutoff_frequency_hz=320,gain_db=-1.0,q=.9),
                     PeakFilter(cutoff_frequency_hz=3150,gain_db=1.2,q=.82)])
dry=chain(dry.T,SR).T
mid=dry.mean(1,keepdims=True)
dry=mid+(dry-mid)*.87
# Very short item fades sit in the boundary air around whole syllables.
dry=fade(dry,.006,.022)
dry*=db(active(old)+.12-active(dry))
assert np.max(abs(dry))<1.15

# Carry the last syllable's room into the next downbeat while the
# recorded Runaway lift supplies the actual musical transition.
tail=n(.48)
room_in=np.pad(band(dry[-n(.41):],390,5400),((0,tail),(0,0)))
room=Reverb(room_size=.47,damping=.65,wet_level=1.,dry_level=0.,width=.85)
tail_signal=room(room_in.T,SR).T[-tail:]
tail_signal=fade(tail_signal,.012,.26)*.17
voice=np.concatenate((dry,tail_signal))
tracks[voice_index]=set_field(tracks[voice_index],'POSITION',seconds(at))
tracks[voice_index]=set_field(tracks[voice_index],'LENGTH',seconds(len(voice)))
label=f'{take.performer} | {take.title}'
tracks[voice_index]=re.sub(r'(?m)^(    +NAME )"[^"]+"$',lambda m:m[1]+f'"{label}"',tracks[voice_index])
print_media(voice_index,voice,f'{take.performer} - {take.title} lead.wav')

# Give the new voice a little room on stressed phrases by trimming only
# the middle of the backing. Native kicks, cymbals and bar positions stay.
bed=load(project/media_path(tracks[bed_index]))
bed_at=n(field(tracks[bed_index],'POSITION'))
a,b=at-bed_at,at+len(dry)-bed_at
native=bed[a:b].copy()
centre=native.mean(1,keepdims=True)
fx=Pedalboard([PeakFilter(cutoff_frequency_hz=1120,gain_db=-2.1,q=.85),
               PeakFilter(cutoff_frequency_hz=2520,gain_db=-1.2,q=1.05)])
difference=fx(centre.T,SR).T-centre
power=gaussian_filter1d(blocks(band(dry,500,3200)),1.35)
env=np.sqrt(power)
weight=np.clip((env/(np.percentile(env,70)+1e-10)-.21)*1.38,0,1)
weight=np.interp(np.arange(len(dry)),(np.arange(len(weight))+.5)*n(.025),weight)
weight*=np.interp(np.arange(len(dry)),[0,n(.065),len(dry)-n(.15),len(dry)-1],[0,1,1,0])
bed[a:b]+=difference*weight[:,None]
print_media(bed_index,bed,f'Runaway backing - {take.performer} verse.wav')

title="Don't Open My Email"
artist=f'Kanye West, {take.performer} & Veer'
for old_artist in ['Kanye West, 21 Savage & Veer']:
    header=header.replace(old_artist,artist)
header=header.replace('Blame Me for Everything',title)
header=header.replace('Upright answer into Savage',f'Upright answer into {take.performer}')
header=header.replace('21 Savage | Creepin',label)
rpp=header+''.join(tracks)+'>\n'
(stage/'Session.rpp').write_text(rpp)
new_files={f.name for f in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((media if m[1] in new_files else project/'Media')/m[1]),rpp)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage}/Full.mp3"',render)
(stage/'Render.rpp').write_text(render)
# Same in-context range for comparing approaches. Full renders use the
# approved master settings, so extracts inherit those settings as well.
report={'source':take.title,'source_cut':[take.start,take.stop],
        'source_bpm':take.tempo,'vocal_start':at/SR,'dry_end':(at+len(dry))/SR,
        'lift':lift/SR,'vocal_active_db':round(active(dry),2),
        'old_vocal_active_db':round(active(old),2),
        'verse_level_change_db':round(rms(bed[a:b])-rms(native),2)}
(stage/'check.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
