"""Print the new guitar, keys, strings, and early drum pickup from MIDI."""
from pathlib import Path
import subprocess
import sys

import numpy as np
from pedalboard import Reverb
import pretty_midi
import soundfile as sf

here = Path(__file__).resolve().parent
shared = here.parents[3]/'shared'
sys.path.insert(0, str(shared))
from dsp import SR, db, fade, filt

beat = 60/87
bar = 4*beat
duration = 56*bar+1
font = shared/'composition/instruments/GeneralUser GS/GeneralUser-GS.sf2'
parts = {name: [] for name in ('Guitar', 'Strings', 'Keys', 'Bass', 'Drums')}

def note(name, measure, offset, pitch, beats, velocity):
    start = measure*bar + offset*beat
    parts[name].append(pretty_midi.Note(velocity,pitch,start,start+beats*beat))

# A short descending answer leaves the original high piano room above it.
# The first four bars expand from E add9 into a B/D# voicing.
guitar = [
    [(0,52,1.4,78),(.78,59,.62,57),(1.55,66,.72,63),(2.45,68,1.2,73),(3.32,64,.78,58)],
    [(.28,63,.8,63),(1.18,59,1.44,68),(2.52,56,.85,59),(3.37,59,.66,61)],
    [(0,51,1.72,74),(.74,58,.8,57),(1.48,63,.93,66),(2.42,66,.8,63),(3.38,63,.66,55)],
    [(.25,59,.84,65),(1.23,58,.70,58),(2.04,56,1.45,63),(3.48,63,.60,54)],
]
for measure, phrase in enumerate(guitar):
    for at,pitch,length,vel in phrase:
        note('Guitar',measure,at,pitch,length,vel)

voicings = [(52,56,59,66), (52,56,59,63),
            (51,54,59,66), (51,54,59,63),
            (49,56,59,64), (49,52,56,63),
            (45,52,56,59), (45,52,57,64)]
for measure,pitches in enumerate(voicings):
    for i,pitch in enumerate(pitches):
        note('Strings',measure,.06*i,pitch,3.97-.04*i,42+i%2*5+min(9,measure))
    if 1<=measure<=4:
        note('Bass',measure,0,pitches[0]-12,2.25,76)
        note('Bass',measure,2.75,pitches[0]-12,1.04,58)
    if measure in (2,3):
        for at,pitch,vel in ((0,36,58),(1,37,44),(2.72,36,46),(3,37,49),(3.56,42,40)):
            note('Drums',measure,at,pitch,.16,vel)
    if measure>=4:
        for at,pitch,length,vel in [(1.46,pitches[2],1.1,63),(3.18,pitches[3],.77,54)]:
            note('Guitar',measure,at,pitch,length,vel)

# That same descending interval becomes a mid-register answer through
# the verses. The voicings follow the two-bar harmony of the recorded bass.
answers = [
    (16,[(1.48,68),(2.48,66),(3.22,64)]),(17,[(1.22,63),(2.34,59)]),
    (19,[(2.76,63),(3.44,66)]),(21,[(2.91,64),(3.48,61)]),
    (23,[(2.38,64),(3.22,59)]),(25,[(2.25,68),(3.39,64)]),
    (27,[(2.80,66),(3.48,63)]),(29,[(2.88,64),(3.44,61)]),
    (30,[(.16,64),(1.49,59),(2.51,56)]),(31,[(.16,59),(1.35,57),(2.63,52)]),
    (34,[(2.88,66),(3.42,63)]),(36,[(2.60,64),(3.31,61)]),
    (39,[(2.60,64),(3.40,59)]),
    (40,[(.22,68),(1.16,66),(2.28,64),(3.20,59)]),
    (41,[(.12,63),(1.31,59),(2.42,56),(3.35,64)]),
    (42,[(.20,69),(1.14,68),(2.30,64),(3.26,59)]),
    (43,[(.19,66),(1.46,64),(2.60,59)]),
    (52,[(.08,64),(1.30,59),(2.62,56)]),
    (53,[(.15,66),(1.16,64),(2.56,59)]),
    (54,[(.13,63),(1.30,59),(2.38,56)]),
    (55,[(.10,64),(1.45,59),(2.52,52)]),
]
for measure,phrase in answers:
    for i,(at,pitch) in enumerate(phrase):
        note('Guitar',measure,at,pitch,.80 if i else 1.08,62-i*4)
        if measure in (16,17,30,31,40,41,42,43,52,53,54,55) and i in (0,2):
            note('Keys',measure,at+.045,pitch-12,1.22,50-i*5)

swells = [(16, (52,59,66)),(18,(51,59,66)),(22,(45,52,64)),
          (26,(51,59,66)),(28,(49,56,64)),(30,(45,52,59)),
          (32,(52,56,59)),(36,(49,56,64)),(38,(45,52,64)),
          (40,(52,56,59,66)),(42,(45,52,57,64)),
          (44,(52,56,59,68)),(46,(51,54,59,66)),
          (48,(49,52,56,64)),(50,(45,52,57,64)),
          (52,(52,56,59,66)),(54,(52,56,59,64))]
for measure,pitches in swells:
    for i,pitch in enumerate(pitches):
        note('Strings',measure,.10*i,pitch,7.94-.13*i,48+(measure>=40)*8-i*3)

midi_dir = here/'MIDI'
midi_dir.mkdir(exist_ok=True)
for name,program,target in [('Guitar',27,-24),('Strings',49,-25),('Keys',4,-25),
                            ('Bass',33,-24),('Drums',0,-25)]:
    midi = pretty_midi.PrettyMIDI(initial_tempo=87,resolution=960)
    instrument = pretty_midi.Instrument(program,is_drum=name=='Drums',name=name)
    instrument.notes.extend(parts[name])
    midi.instruments.append(instrument)
    path = midi_dir/f'{name}.mid'
    midi.write(str(path))
    raw = here/f'{name} raw.wav'
    subprocess.run(['fluidsynth','-ni','-q','-g','.70','-r',str(SR),
                    '-o','synth.reverb.active=0','-F',str(raw),str(font),str(path)],check=True)
    x,rate = sf.read(raw,dtype='float32',always_2d=True)
    assert rate==SR
    x = filt(x,'highpass',34 if name in ('Drums','Bass') else 118)
    if name not in ('Drums','Bass'):
        x = filt(x,'lowpass',5300)
        x = Reverb(room_size=.47,damping=.60,wet_level=.22,dry_level=.86,width=.91)(x.T,SR).T
    if name=='Guitar':
        offset = round(.75*beat*SR)
        x[offset:] += x[:-offset,::-1].copy()*.15
    n = len(x)//8820
    p = (x[:n*8820].reshape(n,-1)**2).mean(1)
    x *= db(target)/np.sqrt(p[p>p.max()*.085].mean())
    frames = round(duration*SR)
    x = np.pad(x,((0,max(0,frames-len(x))),(0,0)))[:frames]
    sf.write(here/f'Veer {name}.wav',fade(x,.006,.8),SR,'FLOAT')
    raw.unlink()
