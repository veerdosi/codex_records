"""Build the guitar interlude and Juice's return from the album project."""
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

import numpy as np
from pedalboard import Reverb
import pretty_midi as pm
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
shared = root/'work/shared'
sys.path.insert(0,str(shared))
from dsp import SR, db, fade, filt, load
toolkit = shared/'composition'
project = root/'reaper/50 Calls'
media = project/'Media'
start = 56.25
duration = 6.0


def score(part, program, notes):
    m = pm.PrettyMIDI(initial_tempo=80,resolution=960)
    instrument = pm.Instrument(program,name=part)
    for note,at,length,velocity in notes:
        instrument.notes.append(pm.Note(velocity,pm.note_name_to_number(note),at,at+length))
    m.instruments.append(instrument)
    path = here/f'{part}.mid'
    m.write(str(path))
    return path


def finish(path, audio, target):
    audio = audio[:round(duration*SR)]
    audio = fade(audio,.018,.3)
    audio *= db(target)/max(np.sqrt(np.mean(audio**2)),1e-8)
    assert abs(audio).max()<.8
    sf.write(media/path,audio,SR,'PCM_24')


piano = score('Return piano',0,[
    ('D4',0,.68,54),('A4',.395,.56,47),('F#4',.77,.63,46),
    ('B4',1.515,.67,55),('D5',2.250,.52,59),('F#5',2.64,.62,55),
    ('D5',3.188,.49,52),('G5',3.76,.71,57),('B4',3.775,.94,52),
])
raw = here/'Piano print.wav'
font = toolkit/'instruments/GeneralUser GS/GeneralUser-GS.sf2'
subprocess.run(['fluidsynth','-ni','-q','-g','.55','-r',str(SR),
    '-F',str(raw),str(font),str(piano)],check=True)
x = filt(load(raw),'highpass',175)
x = np.pad(x,((0,max(0,round(duration*SR)-len(x))),(0,0)))
verb = Reverb(room_size=.55,damping=.62,wet_level=.27,dry_level=.83,width=.86)
finish('Veer - Return piano.wav',verb(x.T,SR).T,-34.1)

strings = score('Return strings',49,[
    ('D3',.745,2.48,44),('A3',.96,1.55,42),('B3',1.95,1.68,43),
    ('F#4',2.23,1.50,50),('G3',3.75,1.85,49),
    ('D4',3.755,1.62,43),('B4',3.77,.93,39),
])
raw = here/'Strings print.wav'
font = toolkit/'instruments/GeneralUser GS/GeneralUser-GS.sf2'
subprocess.run(['fluidsynth','-ni','-q','-g','.55','-r',str(SR),
    '-F',str(raw),str(font),str(strings)],check=True)
x = filt(filt(load(raw),'highpass',160),'lowpass',4450)
t = np.arange(len(x))/SR
shape = np.interp(t,[0,.74,1.8,2.7,3.38,3.68,3.75,4.05,5.8,6],[0,0,.40,.66,1.1,.9,.39,.62,.07,0])
finish('Veer - Return strings.wav',x*shape[:,None],-34.7)

# Soft wooden rim taps and a low drum pick up the final beat into the hook.
taps = [(2.63,.25,204),(3.0,.45,188),(3.185,.26,215),(3.375,.54,148)]
x = np.zeros((round(SR*duration),2),np.float32)
rng = np.random.default_rng(50)
for j,(at,gain,hz) in enumerate(taps):
    t = np.arange(round(.19*SR))/SR
    noise = rng.standard_normal((len(t),2))
    noise = filt(noise,'bandpass',(750,4600))
    ring = np.sin(2*np.pi*(hz*t+1.2*(1-np.exp(-t/.019))))
    env = np.minimum(t/.003,1)*np.exp(-t/.038)
    hit = (.74*ring[:,None]+.32*noise)*env[:,None]*gain
    i = round(SR*at)
    x[i:i+len(t)] += hit*np.array([1+j*.045,1-j*.045])
finish('Veer - Return percussion.wav',x,-37)

original = here.parents[1]/'previous_exports/50 Calls before return transition.rpp'
base = (original if original.is_file() else project/'50 Calls.rpp').read_text()
chunks = re.split(r'(?m)(?=^  <TRACK )',base)
envelopes = [
    (54.95,[(54.95,.90157114),(55.56,.34),(56.24,.07),(57.75,.045),
            (58.86,.055),(59.96,.07),(60,.84),(62.96,.84),(63.01,.89639619)]),
    (54.92,[(54.92,1.01157945),(55.75,.52),(57.85,.29),(59.92,.17),
            (60,.90),(62.96,.90),(63.02,.955)]),
]
for i,(cut,points) in enumerate(envelopes,1):
    def change(match):
        prior = [(float(t),float(y)) for t,y in re.findall(r'^      PT ([\d.]+) ([\d.]+) 0$',match[0],re.M)]
        keep = [(t,y) for t,y in prior if t<cut or t>63.02]
        values = ''.join(f'      PT {t:g} {v:.8f} 0\n' for t,v in sorted(keep+points))
        return re.sub(r'(?m)(?:^      PT [^\n]+\n)+',lambda _:values,match[0],count=1)
    chunks[i],n = re.subn(r'(?ms)^    <VOLENV3\n.*?^    >',change,chunks[i],count=1)
    assert n==1

# Duck the earlier piano phrase as the new answer enters.
piano_track = chunks[-1]
new_env = '''    <VOLENV3
      ACT 1 -1
      VIS 1 1 1
      ARM 0
      DEFSHAPE 0 -1 -1
      VOLTYPE 1
      PT 0 1 0
      PT 55.92 1 0
      PT 56.28 0.12 0
      PT 59.95 0.12 0
      PT 60.24 1 0
    >
'''
chunks[-1] = piano_track.replace('    <ITEM\n',new_env+'    <ITEM\n',1)
track_template = chunks[-1].split('    <VOLENV3',1)[0]
item_template = re.search(r'(?ms)^    <ITEM\n.*?^    >\n',piano_track)[0]

def guid():
    return '{'+str(uuid4()).upper()+'}'


def make_track(name, filename, gain, iid):
    gid = guid()
    track = re.sub(r'\{[0-9A-F-]+\}',lambda _:gid,track_template)
    track = re.sub(r'(?m)^    NAME .*$',f'    NAME "{name}"',track)
    track = re.sub(r'(?m)^    VOLPAN \S+',f'    VOLPAN {db(gain):.9f}',track)
    item = item_template.replace('Interlude piano.wav',filename)
    for field,value in [('POSITION',start),('LENGTH',duration),('IID',iid),('IGUID',guid()),('GUID',guid())]:
        item = re.sub(rf'(?m)^(      {field} ).*$',lambda m:m[1]+str(value),item,count=1)
    return track+item+'  >\n'

chunks[-1] = chunks[-1].rstrip().removesuffix('>').rstrip()+'\n'
result = ''.join(chunks)
result += make_track('Veer | Return piano','Veer - Return piano.wav',0,201)
result += make_track('Veer | Return strings','Veer - Return strings.wav',0,202)
result += make_track('Veer | Return percussion','Veer - Return percussion.wav',0,203)
result += '>\n'
result = result.replace('"Instrumental release"','"False ending and return pickup"')
(here/'50 Calls revised.rpp').write_text(result)
