"""Write the original instruments and print editable MIDI and separate audio."""
from pathlib import Path
from functools import lru_cache
import re
import subprocess
import sys

import numpy as np
import pretty_midi as midi
from pedalboard import Reverb
import soundfile as sf
from scipy.signal import resample_poly

song = Path(__file__).resolve().parent
shared = song.parents[1]/'shared'
sys.path.insert(0,str(shared))
from dsp import SR, db, fade, filt

tools = shared/'composition/instruments'
score = song/'score'
score.mkdir(exist_ok=True)
analysis = song/'analysis'
fast = 60/87
slow = fast*1.25
chorus_end = 68*fast
slow_start = chorus_end+5*fast
verse = slow_start+4*slow
verse_end = verse+40*slow
kanye = verse_end+4*slow
hook2_end = kanye+24*4*fast
duration = hook2_end+10.45

notes = {name: [] for name in ('Strings','Guitar','Bass','Drums')}
def note(part,t,p,length,v):
    notes[part].append((t,p,length,v))

# Each four-bar passage moves from E through G-sharp minor and C-sharp minor
# toward A. The opening motif returns in a lower register under Savage.
harmony = [
    (40,(52,59,63,68)),
    (39,(54,59,63,66)),
    (37,(52,56,61,64)),
    (33,(52,57,59,64)),
]
intro = [
    (0.0,64,2.1,70),(1.52,68,1.02,58),(2.37,66,1.15,55),
    (4.06,63,1.8,67),(5.44,59,1.45,64),(6.26,61,1.17,56),
    (8.37,64,1.13,58),(9.26,66,.92,52),(10.12,68,.78,58),
    (12.35,69,1.42,60),(13.72,64,1.45,55),(14.69,59,.72,49)
]
for t,p,d,v in intro:
    note('Guitar',t*fast,p,d*fast,v)
for bar,(root,chord) in enumerate(harmony):
    start=bar*4*fast
    for i,p in enumerate((root+12,chord[1],chord[2])):
        note('Strings',start+i*.075,p,3.96*fast,49-i*7+(bar%2)*4)
    if bar>=1:
        note('Bass',start+.56,root,1.10,37)

# Fade the score down as the original high piano takes over.
for bar in range(3):
    t=(bar+4)*4*fast
    for i,p in enumerate((45,52,59) if bar<2 else (47,54,59)):
        note('Strings',t+i*.09,p,3.9*fast,41-i*6)
    if bar==2:
        note('Guitar',t+2.25*fast,71,1.35*fast,49)
for i,p in enumerate((45,52,59,64)):
    note('Strings',19.66+i*.10,p,2.85-i*.10,48-i*5)
note('Guitar',20.02,64,1.44,49)
for at,p in [(26.75,76),(31.6,75),(37.0,73),(43.2,69)]:
    note('Guitar',at,p,.45,43)

# Five quarters of the original tempo have the same duration as four
# quarters of the verse tempo. The bowed notes sustain over that change.
for i,p in enumerate((45,52,59,64)):
    note('Strings',chorus_end-.4+i*.09,p,4.9-i*.18,62-7*i)
for at,p,v in [(0,64,66),(1.04,61,63),(2.56,59,55),(3.43,68,61)]:
    note('Guitar',chorus_end+at,p,1.0,v)
for at,velocity,pitch in [(0,80,36),(1.25,42,42),(2.5,71,37),(3.75,45,42)]:
    note('Drums',chorus_end+at*fast,pitch,.18,velocity)

# Kick and backbeat fit Savage's slower meter. Keep the piano accents in
# the foreground, with a counterline that moves at the ends of phrases.
for bar in range(11):
    t=slow_start+bar*4*slow
    root,chord=harmony[(bar-1)%4]
    for at,p,v in [(0,36,105),(1,38,91),(2.5,36,88),(3,38,96)]:
        if bar==0 and at==2.5:
            continue
        note('Drums',t+at*slow,p,.17,v)
    if bar%2==0 and bar>1:
        note('Drums',t+3.25*slow,36,.15,82)
    for i in range(8):
        note('Drums',t+(i*.5+(.015 if i%2 else 0))*slow,42,.07,51 if i%2==0 else 35)
    if bar in (3,6,8,10):
        for at,p,v in ((3.25,42,39),(3.75,46,55)):
            note('Drums',t+at*slow,p,.11,v)
    for at,p,length,v in [(0,root,1.52,90),(1.76,root+7,.34,65),(2.49,root,1.10,85)]:
        note('Bass',t+at*slow,p,length*slow,v)
    if bar%4 in (1,2,0):
        for i,p in enumerate((root+12,chord[1],chord[2])):
            note('Strings',t+i*.066,p,3.98*slow,49-i*5+((bar//4)%2)*5)
    lick=[(0.5,chord[-1],.53,63),(1.67,chord[1],.70,54),(3.24,chord[2],.48,59)]
    if bar%4 in (0,3):
        lick=[(.19,chord[2],.82,61),(2.05,chord[-1],.43,53),(3.13,chord[1],.68,57)]
    for at,p,d,v in lick:
        note('Guitar',t+at*slow,p,d*slow,v)
    if bar in (4,8,10):
        note('Guitar',t+3.63*slow,chord[-1]+12,.26,47)

# The pulse stays audible through the return to Kanye.
note('Bass',verse_end+.012,33,1.24,61)
note('Bass',verse_end+1.75*slow,35,1.07,58)
for i,p in enumerate((45,52,56,59)):
    note('Strings',verse_end-.28+i*.11,p,4.2,55-i*6)
for i,(p,v) in enumerate(((76,64),(75,57),(73,51),(71,49))):
    note('Guitar',kanye-3*fast+i*.7*fast,p,.66,v)
for i in range(3):
    note('Drums',kanye-(3-i)*fast,37,.12,40+i*7)

# A sparse answer in the quieter Kanye verse and a wider final chorus.
for bar in (0,3,5,7,11,15,17,20,22):
    t=kanye+bar*4*fast
    root,chord=harmony[(bar//2)%4]
    for i,p in enumerate((root+12,chord[1],chord[2])):
        note('Strings',t+.43+i*.10,p,3.3*fast,44-i*5+(bar>=16)*6)
    note('Guitar',t+2.62*fast,chord[-1]+12,.64,43 if bar<16 else 49)
for i,(p,v) in enumerate(((76,69),(71,61),(68,58),(66,54),(64,51))):
    note('Guitar',hook2_end+.43+i*1.24,p,1.32,v)
for i,p in enumerate((40,52,59,68)):
    note('Strings',hook2_end-.12+i*.11,p,8.3-i*.44,55-i*8)

def write_midi(name, events, program):
    m=midi.PrettyMIDI(initial_tempo=87,resolution=960)
    instrument=midi.Instrument(program,is_drum=name=='Drums',name=name)
    for t,p,length,v in events:
        instrument.notes.append(midi.Note(v,p,t,t+length))
    m.instruments.append(instrument)
    path=score/f'{name}.mid'
    m.write(str(path))
    return path

def level(x,target):
    blocks=len(x)//11025
    env=(x[:blocks*11025].reshape(blocks,-1)**2).mean(1)
    active=env[env>env.max()*.06]
    return x*min(db(target)/np.sqrt(active.mean()),.78/max(abs(x).max(),1e-8))

def pad(x):
    total=round(duration*SR)
    return np.pad(x,((0,max(0,total-len(x))),(0,0)))[:total]

for name,program,target in [('Strings',49,-28.5),('Guitar',27,-28)]:
    path=write_midi(name,notes[name],program)
    raw=analysis/f'{name} raw.wav'
    font=tools/'GeneralUser GS/GeneralUser-GS.sf2'
    subprocess.run(['fluidsynth','-ni','-q','-g','.68','-r',str(SR),
        '-o','synth.reverb.active=0','-F',str(raw),str(font),str(path)],check=True)
    x,s=sf.read(raw,dtype='float32')
    assert s==SR
    x=filt(filt(x,'highpass',125 if name=='Strings' else 160),'lowpass',4900)
    room=Reverb(room_size=.63,damping=.63,wet_level=.29,dry_level=.80,width=.88)
    x=pad(room(x.T,SR).T)
    if name=='Guitar':
        delay=round(.48*SR)
        x[delay:]+=x[:-delay,::-1].copy()*.14
    sf.write(analysis/f'Veer {name}.wav',fade(level(x,target),.035,.75),SR,'FLOAT')

write_midi('Bass',notes['Bass'],38)
x=np.zeros((round(duration*SR),2),np.float32)
for t,p,length,v in notes['Bass']:
    n=round((length+.075)*SR)
    seconds=np.arange(n)/SR
    hz=440*2**((p-69)/12)
    env=np.minimum(1,seconds/.011)*np.clip((length+.075-seconds)/.075,0,1)
    wave=np.tanh(1.27*np.sin(2*np.pi*hz*seconds)+.16*np.sin(4*np.pi*hz*seconds))*env
    wave=filt(wave,'lowpass',315)*(v/100)**1.2
    at=round(t*SR)
    x[at:at+n]+=wave[:,None]
sf.write(analysis/'Veer Bass.wav',level(x,-24.0),SR,'FLOAT')

kit=next((tools/'AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
groups={}
for group in kit.read_text().split('<group>')[1:]:
    key=re.search(r'\bkey=(\d+)',group.split('<region>',1)[0])
    if key:
        groups[int(key[1])]=[(int(top),kit.parent/path)
            for top,path in re.findall(r'hivel=(\d+) sample=([^\r\n]+)',group)]

@lru_cache(maxsize=48)
def drum(p,v):
    path=next(path for top,path in groups[p] if v<=top)
    wave,s=sf.read(path,dtype='float32',always_2d=True)
    if s!=SR:
        from math import gcd
        d=gcd(s,SR)
        wave=resample_poly(wave,SR//d,s//d,axis=0)
    if wave.shape[1]==1:
        wave=np.repeat(wave,2,axis=1)
    start=np.flatnonzero(np.max(abs(wave),axis=1)>np.max(abs(wave))*.023)[0]
    wave=fade(wave[max(0,start-16):start+round(SR*.27)],.001,.048)
    return wave*(v/100)*{36:1.00,38:.92,37:.70,42:.35,46:.29}[p]

write_midi('Drums',notes['Drums'],0)
x=np.zeros((round(duration*SR),2),np.float32)
for t,p,_,v in notes['Drums']:
    hit=drum(p,v)
    at=round(t*SR)
    x[at:at+len(hit)]+=hit
sf.write(analysis/'Veer Drums.wav',level(filt(x,'highpass',28),-21.0),SR,'FLOAT')
print('Time map',chorus_end,slow_start,verse,verse_end,kanye,hook2_end,duration)
