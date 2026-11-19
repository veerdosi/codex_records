"""Arrange Shreya Ghoshal's film performance against a new guitar and drum score."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import math
import subprocess
import sys

import mido
import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter1d
import soundfile as sf

P = Path(__file__).resolve().parent
SHARED = P.parent.parent/'shared'
sys.path.insert(0, str(SHARED))
from dsp import load, filt, fade, db, SR

BPM = 85.42
BEAT = 60/BPM
PHASE = .408
RNG = np.random.default_rng(755)
DIR = P/'stems'/'arrangement'
DIR.mkdir(parents=True, exist_ok=True)
MIDI = P/'midi'
MIDI.mkdir(exist_ok=True)
GUITAR = P/'sources/instruments/clean-electric.sf2'
BASS = SHARED/'composition/instruments/GeneralUser GS/GeneralUser-GS.sf2'
KIT = SHARED/'composition/instruments/AVL Drumkits/BLACK_PEARL_2023_repack'

# Source bars 1–78, with changes at beats 1 and 3.
SOURCE = '''
Bbm Gb Fs/Fm Bbm Bbm Gb Fs/Fm Bbm Ab Gb/Ebm Fm Gb Gb Fs/Eb5
Bbm Gb Ab Fm/Gb Bbm Ebm Ab Fs/Gb Bbm Eb5 Bbm/Db Eb5/Cm Bbm Bbm Ab/Eb5 Ab/Eb5 Gb/Db Ebm Fs/Ebm F
Bbm Gb Bbm Gb Bbm Bbm/Gb Gb/Bbm Bbm/Gb Gb/Bbm Bbm/Gb Gb/Fm Fm/Bbm Bbm Bbm/Gb Gb/Bbm Bbm/Gb Gb/Fm Fm/Bbm Bbm Bbm/Gb Gb/Fm Fm/Bbm Bbm/Ab Ab/Gb Ebm/Fm Fm/Gb Gb Gb/Bbm Bbm/Ebm Ebm/Bbm Db/Ebm Ebm/Bbm Fs/Bbm F/Ab Fm/Ab Fm/Gb Gb/Ebm Ebm/F Fs Gb Ebm Bbm Bbm Bbm
'''.split()
assert len(SOURCE)==78, len(SOURCE)
# Power voicings and upper strings. Fs means Fsus4.
ROOTS = {'Bbm':34,'Gb':30,'Ab':32,'Fm':29,'Fs':29,'F':29,'Ebm':39,'Eb5':39,'Db':37,'Cm':36}
VOICES = {
    'Bbm':(46,53,58,61,65), 'Gb':(42,49,54,58,65), 'Ab':(44,51,56,60,63),
    'Fm':(41,48,53,56,60), 'Fs':(41,48,53,58,60), 'F':(41,48,53,57,60),
    'Ebm':(51,58,63,66,70), 'Eb5':(51,58,63,65,70), 'Db':(49,56,61,65,68),
    'Cm':(48,55,60,63,67),
}

@dataclass(frozen=True)
class Region:
    start: int
    stop: int
    section: str

# The film edit contains dialogue after the first refrain. The rendered
# interlude bridges the last sung cadence to the second verse.
INTRO_BEATS = 16
CUTS = [
    Region(0,32,'verse'), Region(32,56,'verse rise'),
    Region(56,88,'prechorus'), Region(88,104,'prechorus lift'),
    Region(104,118,'chorus'), Region(118,130,'guitar interlude'),
    Region(194,222,'verse2'), Region(222,246,'lift'),
    Region(246,262,'last prechorus'), Region(262,292,'chorus2'),
    Region(292,304,'outro'),
]
END = INTRO_BEATS
SECTIONS = []
for region in CUTS:
    SECTIONS.append((END, region))
    END += region.stop-region.start

# Start the clips ahead of their grid anchor to retain the initial pickup.
VOCAL_CUES = []
for first, last, pickup in [(0,118,PHASE), (194,292,.38)]:
    pos=next(at for at,r in SECTIONS if r.start==first)
    VOCAL_CUES.append({
        'source_start': PHASE+first*BEAT-pickup,
        'source_end': PHASE+last*BEAT,
        'mix_start': pos*BEAT-pickup,
    })
TAIL = 2.25
SIZE = round((END*BEAT+TAIL)*SR)

def blank():
    return np.zeros((SIZE,2),dtype=np.float32)

def place(bus, x, sec, gain=1., pan=0.):
    index = round(sec*SR)
    if index < 0:
        x = x[-index:]
        index=0
    count = min(len(x), len(bus)-index)
    if count <= 0:
        return
    x=x[:count]
    if x.ndim == 1:
        bus[index:index+count,0] += x * gain * np.sqrt(1-pan)
        bus[index:index+count,1] += x * gain * np.sqrt(1+pan)
    else:
        balance=np.array([min(1.,1-pan),min(1.,1+pan)],dtype=np.float32)
        bus[index:index+count] += x * (gain * balance)

def tone_at(source_beat):
    return SOURCE[source_beat//4].split('/')[min((source_beat%4)//2,
                                               len(SOURCE[source_beat//4].split('/'))-1)]

def stereo(x, width):
    return x.mean(axis=1,keepdims=True)*(1-width) + width*x

def time_crop(x):
    bus=blank()
    place(bus, x, 0.)
    return bus

def grid_score(events, file, program):
    midi=mido.MidiFile(ticks_per_beat=960)
    track=midi.add_track()
    track.append(mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(BPM)))
    track.append(mido.Message('program_change',program=program))
    queued=[]
    for beat, note, length, strength in events:
        start=max(0,round(960*beat))
        stop=max(start+1,round(960*(beat+length)))
        queued.extend([(start,1,note,strength),(stop,0,note,0)])
    previous=0
    for tick, on, note, vel in sorted(queued):
        track.append(mido.Message('note_on' if on else 'note_off', note=note,
                                  velocity=vel,time=tick-previous))
        previous=tick
    track.append(mido.MetaMessage('end_of_track',time=3840))
    midi.save(file)

def synth(name, events, instrument=GUITAR, program=0):
    midi = MIDI/(name+'.mid')
    wav=DIR/(name+'-dry.wav')
    grid_score(events,midi,program)
    subprocess.run(['fluidsynth','-ni','-C','0','-R','0','-g','0.83','-T','wav','-O','float',
                    '-r',str(SR),'-F',str(wav),str(instrument),str(midi)],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return time_crop(load(wav))

def rms_envelope(x, sec):
    e=uniform_filter1d(np.mean(x*x,axis=1),size=round(sec*SR))
    return np.sqrt(np.maximum(e,1e-12))

def tame(x, threshold, strength=.45, sec=.055):
    env=rms_envelope(x,sec)
    gain=np.maximum(env/threshold,1.)**(-strength)
    return x*uniform_filter1d(gain,size=round(sec*.75*SR))[:,None]

def amp(x, grit, dark=False):
    # Remove excess low swing before clipping, then shape the speaker response.
    mono=stereo(x,.42)
    pre=filt(mono,'bandpass',[92 if dark else 113,6900])
    pre += .32*filt(pre,'bandpass',[330,1430])
    driven=np.tanh(grit*(pre+.09*pre**2))
    pos=filt(driven,'bandpass',[112,4150 if dark else 4950])
    return filt(pos,'lowpass',6500)-.15*filt(pos,'bandpass',[2320,3100])

def room(x, depth, sends, lo, hi):
    out=x.copy()
    filtered=filt(x,'bandpass',[lo,hi])
    for i,(lag,vol) in enumerate(sends):
        place(out, filtered[:,::-1] if i%2==0 else filtered,lag,vol*depth)
    return out

def unit(x, level, q=1):
    e=rms_envelope(x,.11)
    active=e[e>max(1e-6,.025*np.max(e))]
    measure=np.percentile(active,75)**q
    return x*(level/max(1e-7,measure))

@lru_cache(maxsize=None)
def sample(note,layer):
    file=sorted(KIT.glob(f'{note}-*-{layer}.wav'))[0]
    x=load(file)
    peak=np.max(np.abs(x[:min(len(x), round(.045*SR))]))
    start=np.argmax(np.max(np.abs(x),axis=1)>peak*.04)
    x=x[max(0,start-12):]
    return x/max(1e-5,np.max(np.abs(x)))

def drum(bus, at, note, velocity, pan=0.):
    layer=min(5,max(1,math.ceil(velocity/24)))
    hit=sample(note,layer)
    jitter=RNG.normal(0,.005)
    factor=(velocity/110.)**1.35
    location=max(0,at*BEAT+jitter)
    gains={36:.40,37:.22,38:.34,40:.31,41:.33,42:.17,44:.15,
           45:.31,46:.20,48:.20,49:.18,51:.19,57:.17,59:.18}
    gain=gains[note]*factor
    place(bus,hit,location,gain,pan)
    if note in (36,38,40,41,45):
        place(bus, filt(hit,'bandpass',[180,6800])[:,::-1],location+.025,gain*.11)

def note(out, beat, pitch, duration, velocity):
    velocity=int(np.clip(velocity+RNG.normal(0,2.0),12,119))
    beat=beat+float(np.clip(RNG.normal(0,.0055),-.012,.012))
    out.append((beat,pitch,duration,velocity))

def plot_markers():
    markers=[{'start':0.,'end':INTRO_BEATS*BEAT,'source':None,'name':'guitar intro'}]
    markers.extend({'start':pos*BEAT, 'end':(pos+r.stop-r.start)*BEAT,
                    'source':None if r.section=='guitar interlude' else PHASE+r.start*BEAT,
                    'name':r.section} for pos,r in SECTIONS)
    return markers

def produce():
    clean_l, clean_r, drive_l, drive_r, lead, bass = ([] for _ in range(6))
    kit, kick = blank(), blank()
    # A descending motif introduces the sound of the interlude. The F chord
    # at the close leaves the first sung note and tonic plenty of space.
    introduction = [
        [(0.06,46,2.60,57),(.54,53,1.86,54),(1.05,61,1.45,60),(2.04,65,1.55,65),(3.22,60,.58,54)],
        [(0,42,2.28,62),(.47,49,1.26,56),(1.06,58,2.11,56),(1.74,65,1.70,62),(2.85,61,.95,53)],
        [(0,51,2.14,64),(.54,58,1.68,58),(1.04,66,1.31,62),(2.00,65,1.02,65),(2.98,63,.81,58)],
        [(0,41,2.94,63),(.56,48,1.73,56),(1.12,58,1.63,62),(2.37,57,1.25,54)],
    ]
    answers=[(2.55,65,1.07,65),(3.55,61,1.07,60),(5.18,58,1.48,57),
             (6.78,65,1.04,62),(9.51,66,1.46,61),(11.15,65,.97,56),
             (13.51,60,1.06,57),(14.62,57,.79,50)]
    for j,phrase in enumerate(introduction):
        for at,pitch,length,strength in phrase:
            note(clean_l,j*4+at,pitch,length,strength)
    for at,pitch,length,strength in answers:
        note(clean_r,at,pitch,length,strength)
    note(bass,8.0,39,3.42,48)
    note(bass,12.0,29,3.15,50)
    drum(kit,9.5,44,33,-.16)
    drum(kit,11.0,41,42,.18)
    drum(kit,13.0,37,44)
    drum(kit,14.49,45,46,-.15)
    drum(kit,15.02,41,52,.18)
    is_heavy={'chorus','chorus2'}
    for region_start,r in SECTIONS:
        if r.section=='guitar interlude':
            continue
        bars=math.ceil((r.stop-r.start)/4)
        for j in range(bars):
            sec=r.section
            src=r.start+j*4
            pos=region_start+j*4
            length=min(4,r.stop-src)
            order=tone_at(src)
            follow=tone_at(src+2) if length>2 else order
            upper=VOICES[order]
            heavy=sec in is_heavy
            finish=(j==bars-1)
            lift=(sec in {'prechorus lift','last prechorus'} or sec in {'prechorus','lift'} and j>=3)
            quiet=(sec=='outro' or sec in {'verse','verse2'} and j<4)
            velocity=49 if quiet else 62 if heavy else 54
            if sec=='outro':
                velocity=max(34, velocity-3*j)
            elif sec=='verse' and j<4:
                velocity=50+3*j
            # Arpeggios use shared tones in the high register and leave space for the singer.
            pattern=([(0,2),(.84,3),(1.52,4),(2.16,2),(2.83,3),(3.44,4)]
                     if quiet else [(0,2),(.56,3),(1.53,4),(2.04,2),(2.56,3),(3.40,4)])
            if heavy:
                pattern=[(.04,4),(1.46,3),(2.09,4),(3.48,3)]
            for p,idx in pattern:
                if p+.1>=length:
                    continue
                v=VOICES[follow if p>=2 else order][idx]
                duration=min(.69 if heavy else 1.03, length-p-.03)
                note(clean_l,pos+p,v,duration,velocity+3*(idx==3))
                if p in (.84, 1.52,2.83,1.53,3.40,1.46,3.48):
                    up=max(53,v-12) if sec=='outro' else (v+12 if v<=65 else v)
                    note(clean_r,pos+p+.13,up,min(.9,length-p-.16),velocity-8)
            if heavy or lift:
                # Independent left and right takes with different strokes and attacks.
                rhythms=(
                    [(0,1.07),(1.48,.43),(2,1.18),(3.46,.42)] if j%4 in (1,3) else
                    [(0,1.62),(2,.96),(3.19,.64)]
                ) if heavy else [(0,1.60),(2,1.50)]
                for beat, dur in rhythms:
                    if beat+.12 >= length:
                        continue
                    chord=follow if beat>=2 else order
                    pitches=VOICES[chord]
                    hit=96 if heavy and j==0 else 88 if heavy else 57+min(13,j*3)
                    for string,pitch in enumerate(pitches[:3]):
                        note(drive_l,pos+beat+.015*string,pitch,min(dur-.018*string,length-beat-.046),hit-5*string)
                    # The right-hand voicing puts the third above the octave,
                    # leaving the left-hand power chords and the bass clear.
                    for string,pitch in enumerate(pitches[1:4]):
                        shift=.016 if beat%1==0 else .027
                        note(drive_r,pos+beat+shift+.011*string,pitch,
                             min(dur-.015*string,length-beat-.065),hit-8*string)
                if heavy and length>=4:
                    for pickup in (1.77,3.78):
                        chord=VOICES[order if pickup<2 else follow]
                        note(drive_r,pos+pickup,chord[2]+12,.14,66+(j%3)*3)
            if sec=='outro' or heavy and j%4==3 or sec=='verse2' and j in (1,3):
                # Answering lead derived from the power-chord common tones.
                p=2.49 if heavy else .52
                for at,pitch,dur in [(p,upper[4],.71),(p+.81,upper[3],.55),
                                     (p+1.48,VOICES[follow][2],1.10)]:
                    if at+.09<length:
                        note(lead,pos+at,pitch,min(dur,length-at-.04),77 if heavy else 60 if sec=='bridge' else 68)

            if sec!='verse' or j>=1:
                moves=[(0,1.37,0),(1.56,.32,0),(2,1.28,0),(3.50,.34,0)] if heavy else [(0,1.80,0),(2,1.68,0)]
                if heavy and j%4==3:
                    moves[-1]=(3.48,.43,7)
                for beat,duration,interval in moves:
                    if beat+.07<length:
                        root=ROOTS[follow if beat>=2 else order]
                        note(bass,pos+beat,root+interval,min(duration,length-beat-.03),
                             97 if heavy else 78 if lift else 60 if quiet else 66)
            if sec=='verse' and j<2 or sec=='outro' and j>=2:
                continue
            if sec=='outro':
                low=[(0,55-j*7)]
                back=[(2,37+j%2,42-j*6)]
                hat=[(.51,37-j*5),(2.5,30-j*5)]
            elif quiet:
                low=[(0,66),(2.53,48)] if j%2 else [(0,64)]
                back=[(2.0,37,61),(3.75,37,29)]
                hat=[(.5,42),(1.5,32),(2.5,39),(3.5,34)]
            elif heavy:
                low=([(0,105),(.77,77),(2,91),(2.75,78)] if j%2==0 else
                     [(0,104),(1.48,82),(2.50,87)])
                back=[(1.012,38,114),(2.013,40,41),(3.010,38,117)]
                hat=[(i*.5+(i%2)*.018, (78 if i%2==0 else 57) + (4 if i%4==2 else 0))
                     for i in range(8)]
            else:
                low=[(0,84),(2.49,72)] if j%2 else [(0,87),(1.77,64),(2.52,72)]
                back=[(1.012,37 if sec=='verse' and j<3 else 38,74),(3.014,38,85)]
                hat=[(i*.5+(i%2)*.019, 53 if i%2==0 else 38) for i in range(8)]
            for a,v in low:
                if a<length:
                    drum(kick,pos+a,36,v)
            for a,n,v in back:
                if a<length:
                    drum(kit,pos+a,n,v)
            for a,v in hat:
                if a<length:
                    n=51 if heavy and sec=='chorus2' and j>2 and int(a*2)%2==0 else (
                        46 if heavy and 3.4<a<3.6 else 42)
                    drum(kit,pos+a,n,v,-.24)
            if heavy and j%4==0:
                drum(kit,pos,49 if j%8==0 else 57,93,.23)
            if finish and sec in {'prechorus lift','last prechorus','chorus2'} and length==4:
                for a,n,v,pan in [(2.73,40,57,-.05),(3.26,45,79,-.28),(3.53,41,88,.22),(3.77,41,92,.22)]:
                    drum(kit,pos+a,n,v,pan)
    dry_vocal=load(P/'stems/htdemucs/source/vocals.wav')
    voice=blank()
    for cue in VOCAL_CUES:
        a=round(cue['source_start']*SR)
        b=round(cue['source_end']*SR)
        place(voice,fade(dry_vocal[a:b],.045,.085),cue['mix_start'])
    voice=stereo(filt(voice,'bandpass',[124,14600]),.61)
    voice-=.20*filt(voice,'bandpass',[225,415])
    brightness=filt(voice,'highpass',6050)
    voice-=brightness*np.clip((rms_envelope(brightness,.040)-.012)*10,0,.31)[:,None]
    voice=unit(tame(voice,.072,.52),.082)
    voice_tail=room(voice,.72,[(.039,.09),(.066,.065),(.25*BEAT,.057),
                             (.75*BEAT,.112),(1.5*BEAT,.045)],570,4300)-voice

    clean=blank()
    l=synth('clean_left',clean_l)
    r=synth('clean_right',clean_r)
    place(clean,unit(filt(l,'bandpass',[134,8400]),.042),0,pan=-.64)
    place(clean,unit(filt(r,'bandpass',[190,7950]),.032),0,pan=.60)
    clean=room(clean,.95,[(.014,.07),(.041,.095),(.069,.093),
                          (.75*BEAT,.16),(1.5*BEAT,.078),(2.25*BEAT,.058)],360,4600)

    guitars=blank()
    raw=synth('overdrive_left',drive_l)
    place(guitars,unit(amp(raw,15.2,True),.066),0,pan=-.91)
    del raw
    raw=synth('overdrive_right',drive_r)
    place(guitars,unit(amp(raw,13.6),.063),0,pan=.91)
    del raw
    guitars=room(guitars,.65,[(.012,.095),(.039,.12),(.064,.09),(.13,.06)],340,4280)
    guitars=stereo(guitars,1.13)

    raw=synth('answering_electric',lead)
    solo=unit(amp(raw,6.2),.042)
    solo=room(solo,1.2,[(.028,.089),(.068,.087),(.75*BEAT,.29), (1.25*BEAT,.13),
                       (1.5*BEAT,.12),(2.25*BEAT,.07)],360,4900)
    # Build a feedback-like swell from the pitched guitar that actually enters.
    for at,r in SECTIONS:
        if r.section not in {'chorus','chorus2','outro'}:
            continue
        begin=round(at*BEAT*SR)
        raw=clean[begin:begin+round(.83*SR)].copy()
        swell=filt(raw[::-1,::-1],'bandpass',[280,3300])
        swell*=np.linspace(0,1,len(swell),dtype=np.float32)[:,None]**1.7
        place(solo,swell,at*BEAT-.83,.43)

    b=synth('picked_bass',bass,BASS,34)
    bass_bus=unit(stereo(filt(b,'bandpass',[35,3600]),.13),.054)
    bass_bus=tame(bass_bus,.088,.42)
    bass_bus -= .20*filt(bass_bus,'bandpass',[190,349])
    bass_bus *= (1.-np.clip(rms_envelope(kick,.075)*1.1,0,.17))[:,None]
    kit*=.90
    kit += .12*filt(kit,'bandpass',[158,435])
    kit=tame(kit,.14,.28,.040)
    kick=tame(filt(kick,'bandpass',[33,7000]),.17,.27,.045)
    kit+=kick

    seconds=np.arange(SIZE,dtype=np.float32)/SR
    for at,r in SECTIONS:
        if r.section in is_heavy:
            enter, leave=at*BEAT,(at+r.stop-r.start)*BEAT
            rise=np.clip((seconds-enter+.045)/.16,0,1)
            tail=np.clip((leave+.11-seconds)/.32,0,1)
            guitars*=(1+.17*(rise*tail))[:,None]

    mask=np.clip((rms_envelope(filt(voice,'bandpass',[690,4100]),.135)-.010)*16,0,1)
    for bus,amount,band in [(clean,.19,[840,3400]),(solo,.54,[650,3950]),(guitars,.55,[900,3950])]:
        bus-=filt(bus,'bandpass',band)*((amount*mask)[:,None])

    interlude=next(at for at,r in SECTIONS if r.section=='guitar interlude')*BEAT
    for name,bus in [('drums',kit),('bass',bass_bus),('cleans',clean),('overdrive',guitars),('lead',solo)]:
        part=load(P/'stems/interlude'/f'{name}.wav')
        place(bus,fade(part,.013,.19),interlude)
    backing=kit+clean+guitars+solo+bass_bus
    mix=filt(backing+voice+voice_tail,'highpass',27)
    mix=tame(mix,.17,.21,.09)
    mix=fade(mix,.06,.90)
    for name,x in [('vocal',voice),('vocal_space',voice_tail),('drums',kit),('bass',bass_bus),
                   ('cleans',clean),('overdrive',guitars),('lead',solo),('backing',backing),('premaster',mix)]:
        sf.write(DIR/f'{name}.wav',x,SR,subtype='FLOAT')
    (P/'analysis'/'arrangement.json').write_text(json.dumps({
        'bpm':BPM,'phase_in_source_seconds':PHASE,'sections':plot_markers(),
        'vocal_cues':VOCAL_CUES,
        'guitar_clean_notes':clean_l,'guitar_drive_notes':drive_l,'bass_notes':bass
    },indent=2))
    print('Duration', len(mix)/SR,'peak',np.max(np.abs(mix)), 'sections', plot_markers())

if __name__=='__main__':
    produce()
