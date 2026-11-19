"""Restore the Runaway groove and recut the three performances on its bar grid."""
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

import numpy as np
from pedalboard import HighShelfFilter, PeakFilter, Reverb
from scipy.ndimage import gaussian_filter1d
import soundfile as sf

from tune import tune

stage = Path(__file__).resolve().parent
root = stage.parents[4]
title = 'Go Back to the Part Where I Leave'
project = root/'reaper'/title
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

media=stage/'Media'
media.mkdir(exist_ok=True)
ref=stage/'Reference.rpp'
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',ref.read_text())
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
grid=json.loads((stage.parent/'edit-check.json').read_text())
beat=60/87
bar=4*beat
n=lambda t:round(float(t)*SR)
at=lambda i:i/SR
clock=lambda i:f'{at(i):.12f}'
b=lambda i:n(i*bar)
start_replace=b(22)
savage_bar=b(24)
savage_exit=b(34)
bridge_end=b(35)
old_em_bar=b(36)
old_return=b(48)
removed=old_em_bar-bridge_end
em_bar=old_em_bar-removed
return_bar=old_return-removed


def field(track,key):
    return re.search(rf'(?m)^      {key} (\S+)',track)[1]


def set_field(track,key,value):
    return re.sub(rf'(?m)^      {key} .*$',f'      {key} {value}',track)


def name(track):
    return re.search(r'(?m)^    NAME "([^"]+)"',track)[1]


def source_file(track):
    return re.search(r'(?m)^        FILE "Media/([^"]+)"',track)[1]


def band(x,lo,hi):
    return filt(filt(x,'highpass',lo), 'lowpass',hi)


def level(x):
    return float(10*np.log10(max(np.mean(x*x),1e-12)))


def smoothstep(size):
    return (.5-.5*np.cos(np.linspace(0,np.pi,size,dtype=np.float32)))[:,None]


def tone(x, high, mids):
    x = HighShelfFilter(cutoff_frequency_hz=2200,gain_db=high,q=.70)(x.T,SR).T
    return PeakFilter(cutoff_frequency_hz=1060,gain_db=mids,q=.76)(x.T,SR).T


def voice_active(x):
    y=band(x,180,6500)
    size=n(.075)
    e=np.mean(y[:len(y)//size*size].reshape(-1,size,2)**2,axis=(1,2))
    return float(10*np.log10(np.mean(e[e>.08*e.max()])))


def print_media(track, filename, audio, pos=None):
    sf.write(media/filename,audio,SR,'FLOAT')
    track=track.replace(source_file(track),filename)
    if pos is not None:
        track=set_field(track,'POSITION',clock(pos))
        track=set_field(track,'LENGTH',clock(len(audio)))
    return track


bed_track=next(t for t in tracks if name(t)=='Runaway | Instrumental')
bed_at=n(field(bed_track,'POSITION'))
old_bed=load(project/'Media'/source_file(bed_track))
old_source=load(root/'work/songs/blame_me_for_everything/stems/runaway_bed_source_instrumental.wav')
origin=n(214.58-214)
bar_source=lambda i:origin+b(i)

# Remove a known source voice artifact using the equivalent phrase in
# the previous eight-bar cycle at the same drum and chord position.
a,c=n(238.91-214),n(240.40-214)
offset=n(8*bar)
replacement=old_source[a-offset:c-offset]
amount=fade(np.ones_like(replacement),.11,.14)
old_source[a:c]=old_source[a:c]*(1-amount)+replacement*amount

def adjusted_source(source_start,duration,target,high,mids,pre=.19,tail=.18):
    start,end=source_start-n(pre),source_start+duration+n(tail)
    x=tone(old_source[start:end].copy(),high,mids)
    reference=band(x[n(pre):n(pre)+duration],55,11500)
    x*=db(target-level(reference))
    return x,n(pre)

# Restore the E–D#–C#–A cycle at the end of the first hook.
# The D# bass leads into C# as Savage finishes, and the E return
# carries Eminem on the next downbeat with the same kit still running.
savage_music,pre=adjusted_source(bar_source(0),bridge_end-start_replace,-18.25,2.2,1.25)
pickup_time=(np.arange(len(savage_music))-pre)/SR
savage_music*=db(np.interp(pickup_time,[-.19,0,bar,2*bar,3*bar],
                           [-1.8,-1.8,-1.55,-.60,0.0]))[:,None]
em_music,em_pre=adjusted_source(bar_source(0),old_return-old_em_bar,-18.40,2.05,1.0)

def insert_at(dst, pos, src, preroll, stop, overlap):
    start=pos-preroll-bed_at
    end=stop-bed_at+overlap
    count=end-start
    x=src[:count]
    assert len(x)==count
    envelope=np.ones((count,1),np.float32)
    if preroll:
        envelope[:preroll]=smoothstep(preroll)
    if overlap:
        envelope[-overlap:]=1-smoothstep(overlap)
    dst[start:end]=dst[start:end]*(1-envelope)+x*envelope


bed=np.concatenate((old_bed[:bridge_end-bed_at],old_bed[old_em_bar-bed_at:]))
insert_at(bed,start_replace,savage_music,pre,bridge_end,0)
insert_at(bed,em_bar,em_music,em_pre,return_bar,n(.042))

# Voice-specific pocket. The filters work on centre only and preserve
# the drum and bass bands and the stereo width.
def pocket(voice,pos,depth,hz):
    first=pos-bed_at
    backing=bed[first:first+len(voice)]
    mid=backing.mean(axis=1,keepdims=True)
    diff=PeakFilter(cutoff_frequency_hz=hz,gain_db=depth,q=1.12)(mid.T,SR).T-mid
    speech=band(voice,700,3500)
    hop=n(.020)
    y=np.pad(speech,((0,-len(speech)%hop),(0,0)))
    energy=np.sqrt(gaussian_filter1d(np.mean(y.reshape(-1,hop,2)**2,axis=(1,2)),2.8))
    weight=np.clip((energy/max(1e-8,np.percentile(energy,70))-.18)*.95,0,1)
    weight=np.interp(np.arange(len(voice)),(np.arange(len(weight))+.5)*hop,weight)
    backing+=diff*weight[:,None]


sav_track=next(t for t in tracks if name(t).startswith('21 Savage'))
em_track=next(t for t in tracks if name(t).startswith('Eminem'))
sav_pos=n(field(sav_track,'POSITION'))
old_em_pos=n(field(em_track,'POSITION'))
em_pos=old_em_pos-removed
sav_raw=load(project/'Media'/source_file(sav_track))
em_raw=load(project/'Media'/source_file(em_track))
sav_dry=n(grid['savage_end']-grid['savage_start'])
em_dry=n(grid['eminem_end']-grid['eminem_start'])

# Rihanna's last vowel sits at the very head of the old Eminem item.
# Leave the lead-in to the instrumental, then retain Eminem's full pickup.
cut_head=n(24.39-23.43)
em_raw[:cut_head]=0
em_raw[cut_head:cut_head+n(.07)]*=smoothstep(n(.07))
sav_raw[:n(.022)]*=smoothstep(n(.022))
sav,sav_tune=tune(sav_raw,stage/'savage_pitchmap.txt')
em,em_tune=tune(em_raw,stage/'eminem_pitchmap.txt')

sav=tone(sav,1.05,-.34)
em=tone(em,.52,-.43)
# Set levels against the previous active consonant and vowel balance.
# Slightly lower overall lead level as the full backing returns.
sav*=db(voice_active(sav_raw)-.60-voice_active(sav))
em*=db(voice_active(em_raw)-.85-voice_active(em))
pocket(sav,sav_pos,-.85,1740)
pocket(em,em_pos,-1.05,2060)

# Rewind the full closing word three times with a different rewind
# length and replay color at each hit. The last replay's room decays
# across the following piano pickup.
word_start=n(53.17-23.43)
word_stop=n(53.64-23.43)
word=fade(em[word_start:word_stop],.006,.036)
hits=[n(t)-removed for t in grid['repeat_beats']]
rewind_pos=hits[0]-n(.185)
rewind=np.zeros((return_bar+n(.34)-rewind_pos,2),np.float32)
for i,hit in enumerate(hits):
    w=band(word,[180,240,310][i],[6500,5100,4050][i])
    speed=np.linspace(0,1,n([.147,.106,.074][i]))**[1.80,1.65,1.50][i]
    ix=(len(w)-1)*(1-speed)
    back=np.column_stack([np.interp(ix,np.arange(len(w)),w[:,ch]) for ch in range(2)])
    back=fade(back,.014,.016)
    j=hit-rewind_pos
    rewind[j-len(back):j]+=back*db([-25.0,-26.4,-27.0][i]-level(back))
    # Let the direct lead finish once, then echo the whole word cleanly.
    side=np.array([[.98,1.02],[.84,1.13],[1.10,.86]][i])
    forward=w*db([-21.9,-23.6,-24.6][i]-level(w))*side
    rewind[j:j+len(w)]+=forward
    if i==2:
        pad=np.pad(forward,((0,n(.94)),(0,0))).astype(np.float32)
        room=Reverb(room_size=.51,damping=.66,wet_level=1,dry_level=0,width=.84)
        tail=room(pad.T,SR).T*db(-16)
        tail=fade(tail,0,.40)
        rewind[j:j+len(tail)]+=tail

# Add a small register change that answers the last vocal without
# interrupting the drum pulse. The piano uses only E-major common tones.
def add_piano_responses():
    libraries = root/'work/shared/environments/composition-venv/lib'
    sys.path.append(str(next(libraries.glob('python*/site-packages'))))
    import mido
    from subprocess import run
    soundfont=root/'work/shared/composition/instruments/GeneralUser GS/GeneralUser-GS.sf2'
    path=stage/'Piano responses.mid'
    offset=b(22)
    last=return_bar+n(.70)
    score=[
        (b(23)+n(.5*beat),71,58,.65),(b(23)+n(2*beat),76,64,.81),
        (b(23)+n(3*beat),71,49,.67),
        (savage_exit+n(.05*beat),68,64,1.38),(savage_exit+n(1.5*beat),71,52,.94),
        (savage_exit+n(3*beat),78,52,.89),(em_bar+n(.04),76,59,1.21),
        (em_bar+n(3*beat),71,43,.71),
        (hits[-1]+n(.5*beat),78,51,.77),
        (return_bar+n(.04),76,62,1.19),
    ]
    midi=mido.MidiFile(ticks_per_beat=960)
    track=midi.add_track()
    track.append(mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(87)))
    track.append(mido.Message('control_change',control=64,value=72))
    events=[]
    for when,note,vel,length in score:
        tick=round(at(when-offset)*960/beat)
        events.extend([(tick,note,vel),(tick+round(length*960/beat),note,0)])
    prev=0
    for tick,note,velocity in sorted(events):
        track.append(mido.Message('note_on' if velocity else 'note_off',note=note,velocity=velocity,time=tick-prev))
        prev=tick
    track.append(mido.Message('control_change',control=64,value=0,time=480))
    midi.save(path)
    out=stage/'Piano raw.wav'
    run(['fluidsynth','-ni','-g','.6','-r',str(SR),'-F',str(out),
         str(soundfont),str(path)],check=True,capture_output=True)
    piano=load(out)
    out.unlink()
    piano=band(piano,175,6500)
    piano=piano[:last-offset]
    piano=fade(piano,.012,.30)*db(-34.0-voice_active(piano))
    return piano,offset

piano,piano_pos=add_piano_responses()
# Retain a light bed of the original string and guitar mix while the
# newly written response has the foreground.
def old_envelope(track):
    def replace(match):
        points={60.2:.96,60.68:.58,67.92:.65,68.55:.99}
        t=float(match[1])
        if t not in points: return match[0]
        return f'      PT {t:.8f} {points[t]:.4f} 0'
    if name(track) in ('Veer | Strings','Veer | Guitar','Veer | Keys','Veer | Cello transition phrases'):
        return re.sub(r'(?m)^      PT (\S+) \S+ 0$',replace,track)
    return track


def move_items(track):
    chunks=re.split(r'(?m)(?=^    <ITEM\n)',track)
    if len(chunks)==1:
        return track
    close='  >\n'
    chunks[-1]=chunks[-1].removesuffix(close)
    edited=[chunks[0]]
    for item in chunks[1:]:
        pos=n(field(item,'POSITION'))
        end=pos+n(field(item,'LENGTH'))
        if pos>=old_em_bar:
            edited.append(set_field(item,'POSITION',clock(pos-removed)))
            continue
        if end<=bridge_end:
            edited.append(item)
            continue
        if pos<bridge_end:
            edited.append(set_field(item,'LENGTH',clock(bridge_end-pos)))
        if end>old_em_bar:
            raise ValueError(f'Unexpected spanning item {name(track)}')
    return ''.join(edited)+close


new=[]
for track in tracks:
    label=name(track)
    if track==bed_track:
        t=set_field(track,'LENGTH',clock(len(bed)))
        new.append(print_media(t,'Runaway - continuous groove.wav',bed))
    elif track==sav_track:
        new.append(print_media(track,'21 Savage - tuned lead.wav',sav,sav_pos))
    elif track==em_track:
        new.append(print_media(track,'Eminem - tuned lead.wav',em,em_pos))
    elif label=='Veer | Three record rewinds':
        new.append(print_media(track,'Eminem - three revised rewinds.wav',rewind,rewind_pos))
        keys=re.sub(r'\{[0-9A-F-]{36}\}',lambda _: '{'+str(uuid4()).upper()+'}',track)
        keys=re.sub(r'(?m)^      IID .*$', '      IID 181', keys)
        new.append(print_media(keys.replace(label,'Veer | Piano answers between verses'),
                               'Piano answers between verses.wav',piano,piano_pos))
    elif label=='Kanye West | Lead':
        moved=move_items(track)
        a=moved.split('    <ITEM\n')
        a[1]=set_field(a[1],'LENGTH',clock(n(60.30)-n(field(a[1],'POSITION'))))
        a[1]=set_field(a[1],'FADEOUT','1 0.095 0 1 0 0 0 1 0 0 1 0 0')
        new.append('    <ITEM\n'.join(a))
    else:
        new.append(move_items(old_envelope(track)))

def move_markers(match):
    idx=int(match[2])
    pos=n(match[3])
    label=match[4]
    if idx==5:
        label=label.replace('Upright answer into Savage','Runaway groove and piano answer')
    elif idx==7:
        label=label.replace('Original Amaj7–B7 lift','C-sharp minor turn into Eminem')
    if pos>=old_em_bar:
        pos-=removed
    return f'{match[1]}{clock(pos)}{label}'

header=re.sub(r'(?m)^(  MARKER (\d+) )(\S+)( .*)$',move_markers,header)
duration=n(grid['duration'])-removed
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {clock(duration)} 0 1000',header)
portable=header+''.join(new)+'>\n'
(stage/f'{title}.rpp').write_text(portable)
absolute=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',lambda m:str((media if (media/m[1]).is_file() else project/'Media')/m[1]),portable)
(stage/'Review.rpp').write_text(absolute)
info={'tempo':87,'duration':at(duration),'sav_start':at(sav_pos),'sav_end':at(sav_pos+sav_dry),
      'bridge_start':at(savage_exit),'eminem_bar':at(em_bar),'em_start':at(em_pos+cut_head),
      'em_end':at(em_pos+em_dry),'rewind_beats':[at(h) for h in hits],'kanye_return':at(return_bar),
      'sav_tuning':sav_tune,'em_tuning':em_tune}
(stage/'revision.json').write_text(json.dumps(info,indent=2)+'\n')
print(info)
