"""Compose a four-bar 80 BPM intro with editable drum and keys scores."""
from pathlib import Path
import subprocess
import sys
import re
from fractions import Fraction

import numpy as np
from pedalboard import HighpassFilter, LowpassFilter, Pedalboard, Reverb
import pretty_midi as midi
import soundfile as sf
from scipy.signal import resample_poly

folder = Path(__file__).resolve().parent
media = Path(sys.argv[1])
toolkit = folder.parents[4] / 'shared/composition'

rate = 48000
beat = .75
kits = toolkit / 'instruments'
piano = next(kits.glob('FreePats/Upright*/*.sfz'))
drumkit = next(kits.glob('AVL Drumkits/BLACK_PEARL*/*.sfz'))


def render_notes(name, program, events, library, drum=False):
    score = midi.PrettyMIDI(initial_tempo=80,resolution=960)
    instrument = midi.Instrument(program,is_drum=drum,name=name)
    for when, length, pitch, velocity in events:
        instrument.notes.append(midi.Note(velocity,pitch,when*beat,(when+length)*beat))
    score.instruments.append(instrument)
    midi_path = folder / f'{name}.mid'
    score.write(str(midi_path))
    wave_path = media / f'Veer - {name}.wav'
    # Read velocity layers directly so the rendered MIDI attacks are stable
    # even when the offline plug-in host drops a block.
    drum_regions = {}
    if drum:
        for section in library.read_text().split('<group>')[1:]:
            header = section.split('<region>',1)[0]
            key = re.search(r'\bkey=(\d+)',header)
            if key:
                drum_regions[int(key[1])] = [
                    (int(limit),library.parent / path)
                    for limit,path in re.findall(r'hivel=(\d+) sample=([^\n\r]+)',section)
                ]
    else:
        piano_samples = {tag:{} for tag in ('H','L')}
        for path in (library.parent/'samples').glob('*.flac'):
            match = re.fullmatch(r'([A-G]#?-?\d+)v([HL])',path.stem)
            if match:
                piano_samples[match[2]][midi.note_name_to_number(match[1])] = path
    length = int((max((t+l)*beat for t,l,_,_ in events)+1.2)*rate)
    audio = np.zeros((length,2),dtype='float32')
    for when,duration,pitch,velocity in events:
        if drum:
            path = next(path for limit,path in drum_regions[pitch] if velocity<=limit)
            root = pitch
            gain = {36:.77,38:.66,39:.31,42:.29}[pitch]*(velocity/100)**.9
        else:
            samples = piano_samples['L' if velocity<78 else 'H']
            root = min(samples,key=lambda n:abs(n-pitch))
            path = samples[root]
            gain = (velocity/86)**1.45
        sample, source_rate = sf.read(path,dtype='float32',always_2d=True)
        scale = Fraction((rate/source_rate)*2**((root-pitch)/12)).limit_denominator(512)
        sample = resample_poly(sample,scale.numerator,scale.denominator,axis=0)
        if sample.shape[1]==1:
            sample = np.repeat(sample,2,axis=1)
        if drum:
            onset = np.flatnonzero(np.max(np.abs(sample),axis=1)>np.max(np.abs(sample))*.016)[0]
            sample = sample[max(0,onset-24):int(rate*.34)+onset]
            release = min(len(sample),int(.037*rate))
        else:
            sample = sample[:round((duration*beat+.24)*rate)]
            release = min(len(sample),round(.24*rate))
        sample[-release:] *= np.linspace(1,0,release)[:,None]
        start = round(when*beat*rate)
        audio[start:start+len(sample)] += sample*gain
    return wave_path,audio


def voice_level(audio, seconds, fade_start, rms_db, check_end):
    length=round(seconds*rate)
    if len(audio)<length:
        audio=np.pad(audio,((0,length-len(audio)),(0,0)))
    audio=audio[:length]
    fade=round(fade_start*rate)
    audio[fade:] *= np.linspace(1,0,length-fade)[:,None]
    active_rms=np.sqrt(np.mean(audio[:round(check_end*rate)]**2))
    return audio*min(10**(rms_db/20)/active_rms,.68/np.max(np.abs(audio)))


# The same backbeat runs through the four bars. The fourth bar clears room
# for the vocal pickup just before beat three.
drum_notes=[]
kick_pattern = [
    [(0,99),(1.5,76),(2,91),(3.5,69)],
    [(0,96),(1.5,72),(2,88),(3.5,73)],
    [(0,101),(1.5,78),(2,92),(2.75,68),(3.5,73)],
    [(0,98),(1.5,79),(3.5,71)],
]
for bar,kicks in enumerate(kick_pattern):
    for step,vel in kicks:
        drum_notes.append((4*bar+step,.10,36,vel))
    for step,vel in ((1,83),(3,86 if bar<3 else 72)):
        drum_notes.append((4*bar+step+.008,.10,38,vel))
        drum_notes.append((4*bar+step+.018,.09,39,58 if bar<3 else 45))
    for slot in range(8):
        if bar==3 and slot in (4,5):
            continue
        vel = (57,42,51,45,59,41,52,44)[slot] - (5 if bar==3 else 0)
        drum_notes.append((4*bar+slot*.5 + (.013 if slot%2 else 0),.06,42,vel))
for when,vel in ((7.75,46),(11.75,45),(15.75,44)):
    drum_notes.append((when,.05,42,vel))
drum_path,drums=render_notes('intro drums',0,drum_notes,drumkit,drum=True)
drums=Pedalboard([HighpassFilter(28),LowpassFilter(11600)])(drums.T,rate).T
sf.write(drum_path,voice_level(drums,12,11.80,-24.7,9),rate,subtype='PCM_24')

# Em9, Cmaj7, Em into Am7, and B7 for the approach to the existing pickup.
# The lead repeats a short descending answer while the voicing moves beneath it.
keys=[]
chords=[
    (0,1.40,(52,55,59,66),(56,58,61,54)),
    (4,1.46,(52,55,59,62),(55,57,61,55)),
    (8,1.46,(52,55,59,66),(59,59,63,53)),
    (10,1.18,(48,55,57,64),(51,56,60,56)),
    (12,1.55,(51,54,57,59),(56,57,54,58)),
]
for when,length,tones,velocities in chords:
    for j,(pitch,vel) in enumerate(zip(tones,velocities)):
        keys.append((when+j*.012,length,pitch,vel))
for when,length,pitch,vel in [
    (.50,.31,71,68),(1.50,.27,67,63),(2.00,.51,64,70),(3.50,.29,66,55),
    (4.50,.30,71,68),(5.50,.26,67,65),(6.00,.52,64,66),(7.50,.28,62,58),
    (8.50,.30,71,70),(9.50,.28,67,67),(10.00,.48,64,66),(11.50,.32,66,60),
    (12.50,.31,71,65),(13.50,.30,66,58),
]:
    keys.append((when,length,pitch,vel))
keys_path,keys=render_notes('intro keys',0,keys,piano)
keys=Pedalboard([HighpassFilter(150),LowpassFilter(3800),
    Reverb(room_size=.29,damping=.72,wet_level=.16,dry_level=.88,width=.90)])(keys.T,rate).T
delay=round(.375*rate)
keys[delay:] += .12*keys[:-delay,::-1].copy()
sf.write(keys_path,voice_level(keys,11.20,10.17,-29.0,9),rate,subtype='PCM_24')

bass_notes=[
    (0,1.14,40,.13),(1.50,.35,40,.094),(2,.78,40,.12),(3.5,.32,43,.087),
    (4,1.08,36,.125),(5.5,.31,36,.092),(6,.92,36,.121),(7.5,.31,38,.093),
    (8,1.06,40,.128),(9.5,.34,40,.097),(10,1.03,45,.117),(11.5,.28,45,.081),
    (12,1.01,35,.126),(13.50,.33,35,.093),
]
orchestra='''<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=32
nchnls=2
0dbfs=1
instr 1
  iHz = cpsmidinn(p4)
  aEnv linseg 0,.006,1,.064,.75,p3-.07,0
  aRoot oscili p5*aEnv,iHz,1
  aSecond oscili .34*p5*aEnv,iHz*2,1
  aThird oscili .12*p5*aEnv,iHz*3,1
  aVoice tone aRoot+aSecond+aThird,550
  outs aVoice,aVoice
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
'''
csd=folder/'Intro bass.csd'
csd.write_text(orchestra+''.join(f'i 1 {t*beat:.5f} {d*beat:.5f} {n} {v}\n' for t,d,n,v in bass_notes)
    +'f 0 12\ne\n</CsScore>\n</CsoundSynthesizer>\n')
bass_path=media/'Veer - intro bass.wav'
subprocess.run(['csound','-o',str(bass_path),str(csd)],check=True)
bass,sample_rate=sf.read(bass_path,dtype='float32')
assert sample_rate==rate
sf.write(bass_path,voice_level(bass,10.43,10.28,-24.4,9),rate,subtype='PCM_24')


# A short B7 answer just before Diwaari's pickup. The notes clear the vocal
# entry and use the same keys as the intro.
pickup_path,pickup=render_notes('pickup keys',0,[
    (.25,.27,66,61),(.75,.25,69,64),(1.00,.24,71,62),
],piano)
pickup=Pedalboard([HighpassFilter(205),LowpassFilter(3900),
    Reverb(room_size=.25,damping=.70,wet_level=.12,dry_level=.92,width=.86)])(pickup.T,rate).T
sf.write(pickup_path,voice_level(pickup,1.15,.92,-31.2,.95),rate,subtype='PCM_24')
