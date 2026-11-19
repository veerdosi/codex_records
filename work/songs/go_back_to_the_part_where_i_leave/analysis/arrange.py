"""Join the three performances on Runaway and cut a three-repeat rewind into Eminem's verse."""
from pathlib import Path
from uuid import uuid4
import json
import re
import sys

import numpy as np
from pedalboard import PeakFilter
from scipy.ndimage import gaussian_filter1d
import soundfile as sf

here=Path(__file__).resolve().parent
root=here.parents[3]
previous=root/'work/songs/blame_me_for_everything'
trials=here/'verse_selection'
project=root/'reaper/Blame Me for Everything'
reference=previous/'previous_exports/Before slow and reverbed ending/Blame Me for Everything.rpp'
media=here/'Media'
media.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

n=lambda t:round(float(t)*SR)
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',reference.read_text())
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
def grab(pattern,text):
    return re.search(pattern,text,re.M)[1]
def field(item,key):
    return grab(rf'^      {key} (\S+)',item)
def label(track):
    return grab(r'^    NAME "([^"]+)"',track)
def file(track):
    return grab(r'^        FILE "([^"]+)"',track)
def time(x):
    return f'{x/SR:.12f}'
def marker(i):
    return n(grab(rf'^  MARKER {i} (\S+)',header))
def edit(item,key,value):
    return re.sub(rf'(?m)^      {key} .*$',f'      {key} {value}',item)
def level(x):
    return 10*np.log10(max(np.mean(x*x),1e-12))
def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)
def guid():
    return '{'+str(uuid4()).upper()+'}'

beat=60/87
lift_old,kanye_old=marker(7),marker(8)
cut=lift_old-n(4*beat)
removed=lift_old-cut
eminem_bar=kanye_old-removed
insertion=n(48*beat)
change=insertion-removed
kanye_new=kanye_old+change
bed_index=next(i for i,t in enumerate(tracks) if label(t)=='Runaway | Instrumental')
old_voice=next(i for i,t in enumerate(tracks) if label(t).startswith('21 Savage |'))
template=tracks[old_voice]
bed_at=n(field(tracks[bed_index],'POSITION'))
bed=load(project/file(tracks[bed_index]))
i,j,k=[t-bed_at for t in (cut,lift_old,kanye_old)]
source=load(previous/'stems/runaway_bed_source_instrumental.wav')
native=n(214.58-214)
final=n(236.655-214)
four=n(16*beat)
patch_a,patch_b=n(238.91-214),n(240.40-214)
clean=source[patch_a-n(32*beat):patch_b-n(32*beat)]
old=source[patch_a:patch_b].copy()
assert len(old)==len(clean)
w=fade(np.ones_like(clean),.11,.14)
source[patch_a:patch_b]=old*(1-w)+clean*w

insert=np.concatenate((source[native:native+four],source[final:final+insertion-four])).copy()
target=level(band(bed[n(66.21)-bed_at:n(93.4)-bed_at],55,12000))
# Use the source's E opening and later A approach, riding only the
# level difference between the two original passages.
for a,b,gain in [(0,four,-.15),(four,len(insert),.22)]:
    portion=insert[a:b]
    portion*=db(target-level(band(portion,55,12000))+gain)
    portion[:n(.024)]=fade(portion[:n(.024)],.024,0)
insert[four-n(.024):four]=fade(insert[four-n(.024):four],0,.024)
head=bed[:i].copy()
lift=bed[j:k].copy()
post=bed[k:].copy()
for left,right,ms in [(head,lift,.011),(lift,insert,.020),(insert,post,.017)]:
    e=n(ms)
    left[-e:]=fade(left[-e:],0,ms)
    right[:e]=fade(right[:e],ms,0)
bed=np.concatenate((head,lift,insert,post))

def read_voice(mode):
    p=trials/mode
    details=json.loads((p/'check.json').read_text())
    waveform=load(next((p/'Media').glob('*lead.wav')))
    return waveform,n(details['vocal_start']),n(details['dry_end']-details['vocal_start'])

savage,sav_at,sav_len=read_voice('loyalty')
em,em_at,em_len=read_voice('eminem')
em_at+=eminem_bar-marker(6)
assert sav_at+sav_len<cut and em_at+em_len<kanye_new

def pocket(voice,at,length,depth):
    lo,hi=at-bed_at,at+length-bed_at
    centre=bed[lo:hi].mean(1,keepdims=True)
    delta=PeakFilter(cutoff_frequency_hz=1080,gain_db=depth,q=.89)(centre.T,SR).T-centre
    energy=band(voice[:length],520,3400)
    block=n(.025)
    energy=np.pad(energy,((0,-len(energy)%block),(0,0)))
    envelope=np.sqrt(gaussian_filter1d(np.mean(energy.reshape(-1,block,2)**2,axis=(1,2)),1.45))
    weights=np.clip((envelope/max(1e-8,np.percentile(envelope,67))-.19)*1.38,0,1)
    w=np.interp(np.arange(length),(np.arange(len(weights))+.5)*block,weights)
    w*=np.interp(np.arange(length),[0,n(.052),length-n(.12),length-1],[0,1,1,0])
    bed[lo:hi]+=delta*w[:,None]

pocket(savage,sav_at,sav_len,-2.6)
pocket(em,em_at,em_len,-2.35)
bed_name='Runaway backing for three verses.wav'
sf.write(media/bed_name,bed,SR,'FLOAT')
tracks[bed_index]=edit(tracks[bed_index],'LENGTH',time(len(bed))).replace(file(tracks[bed_index]),f'Media/{bed_name}')

# Rewind the last word of Eminem's thought three times. Each backwards
# gesture lands on a forward replay on the next beat, with the original
# kick and bass still playing in the background.
word_at=n(53.235-23.43)
word_stop=n(53.625-23.43)
word=fade(em[word_at:word_stop],.004,.038)
repeat_beats=[eminem_bar+n((44+i)*beat) for i in range(3)]
rewind_at=repeat_beats[0]-n(.21)
rewind=np.zeros((repeat_beats[-1]+n(.51)-rewind_at,2),np.float32)
for index,when in enumerate(repeat_beats):
    play=band(word,205+index*110,6500-index*950)
    direction=np.arange(n(.17))/max(1,n(.17)-1)
    source_position=(len(play)-1)*(1-direction**(1.65+index*.19))
    backwards=np.column_stack([np.interp(source_position,np.arange(len(play)),play[:,ch]) for ch in range(2)])
    backwards=fade(backwards,.019,.019)
    backwards*=db((-25.5+index*.4)-level(backwards))
    forward=play*db((-21.5-index*1.1)-level(play))
    if index==1:
        forward=forward*np.array([.78,1.06],np.float32)
    if index==2:
        forward=forward*np.array([1.04,.77],np.float32)
    a=when-rewind_at
    rewind[a-len(backwards):a]+=backwards
    rewind[a:a+len(forward)]+=forward
    # Make space for the record gesture without punching a hole in the beat.
    l=when-n(.20)-bed_at
    r=when+n(.32)-bed_at
    portion=bed[l:r]
    mids=band(portion,500,5800)
    env=np.interp(np.arange(len(portion))/SR,[0,.062,.19,.31,.52],[0,.55,1,.55,0])
    portion-=mids*env[:,None]*.12

# The bed now also includes the small EQ move under the record effect.
sf.write(media/bed_name,bed,SR,'FLOAT')

def make_track(title,filename,audio,at,iid):
    sf.write(media/filename,audio,SR,'FLOAT')
    t=re.sub(r'\{[0-9A-F-]{36}\}',lambda _:guid(),template)
    t=re.sub(r'(?m)^(    +NAME )"[^"]+"$',lambda m:m[1]+f'"{title}"',t)
    for key,value in [('POSITION',time(at)),('LENGTH',time(len(audio))),('SOFFS',0),('IID',iid)]:
        t=edit(t,key,value)
    return t.replace(file(t),f'Media/{filename}')

new_tracks=[]
iid=130
for idx,track in enumerate(tracks):
    if idx==old_voice:continue
    if idx==bed_index:
        new_tracks.append(track)
        continue
    prefix,*items=re.split(r'(?m)(?=^    <ITEM\n)',track.removesuffix('  >\n'))
    edited=[]
    for item in items:
        pos,length,offset=[n(field(item,key)) for key in ('POSITION','LENGTH','SOFFS')]
        for lower,upper,shift in [(0,cut,0),(lift_old,kanye_old,-removed),(kanye_old,10**9,change)]:
            a,b=max(pos,lower),min(pos+length,upper)
            if b<=a:continue
            clone=edit(item,'POSITION',time(a+shift))
            clone=edit(clone,'LENGTH',time(b-a))
            clone=edit(clone,'SOFFS',time(offset+a-pos))
            if a!=pos:
                clone=re.sub(r'(?m)^(      (?:IGUID|GUID) ).*$',lambda m:m[1]+guid(),clone)
                clone=edit(clone,'IID',iid)
                iid+=1
            edited.append(clone)
    if edited:
        new_tracks.append(prefix+''.join(edited)+'  >\n')
new_tracks.extend([
    make_track('21 Savage | Said N Done','21 Savage - Said N Done lead.wav',savage,sav_at,iid),
    make_track('Eminem | Love the Way You Lie','Eminem - Love the Way You Lie lead.wav',em,em_at,iid+1),
    make_track('Veer | Three record rewinds','Eminem - Three record rewinds.wav',rewind,rewind_at,iid+2),
])

title='Go Back to the Part Where I Leave'
artists='Kanye West, 21 Savage, Eminem & Veer'
length=n(grab(r'^  RENDER_RANGE 0 0 (\S+)',header))+change
header=header.replace('Blame Me for Everything',title).replace('Kanye West, 21 Savage & Veer',artists)
header=header.replace('21 Savage | Creepin','21 Savage | Said N Done')
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {time(length)} 0 1000',header)
def move(m):
    t=n(m[3])
    if int(m[2])==7:t-=removed
    elif int(m[2])>=8:t+=change
    return f'{m[1]}{time(t)}{m[4]}'
header=re.sub(r'(?m)^(  MARKER (\d+) )(\S+)( .*)$',move,header)
for id,at,text in [(13,eminem_bar,'Eminem | Love the Way You Lie'),(14,repeat_beats[0],'Three record rewinds')]:
    header+=f'  MARKER {id} {time(at)} "{text}" 0 0 1 B {guid()} 0 1\n'
rpp=header+''.join(new_tracks)+'>\n'
(here/f'{title}.rpp').write_text(rpp)
names={f.name for f in media.glob('*.wav')}
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
    lambda m:str((media if m[1] in names else project/'Media')/m[1]),rpp)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
report={'savage_start':sav_at/SR,'savage_end':(sav_at+sav_len)/SR,'runaway_lift':cut/SR,
        'eminem_start':em_at/SR,'eminem_end':(em_at+em_len)/SR,'repeat_beats':[a/SR for a in repeat_beats],
        'kanye_downbeat':kanye_new/SR,'duration':length/SR}
(here/'edit-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
