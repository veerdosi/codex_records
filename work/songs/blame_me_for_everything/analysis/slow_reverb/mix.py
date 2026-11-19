"""Render the final chorus and outro with a slower pulse and a longer room."""
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from pedalboard import Reverb
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
alternates = here.parents[1] / 'alternates'
alternates.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load

n = lambda t: round(t*SR)
reference = (here/'Reference.rpp').read_text()
chorus_at = n(float(re.search(r'(?m)^  MARKER 11 (\S+)',reference)[1]))
outro_at = n(float(re.search(r'(?m)^  MARKER 12 (\S+)',reference)[1]))
base = 87
slow = 77
mix = load(here/'Premaster.wav')
head = n(.12)
segment = mix[chorus_at-head:]
dry_in = here/'Final section source.wav'
dry_out = here/'Final section stretched.wav'
sf.write(dry_in,segment,SR,'FLOAT')

# Let the first downbeat arrive with the existing pulse, then settle
# to 77 BPM over four beats. Stretch time with pitch preserved.
beat = 60/base
stretch = base/slow
ramp = 4*beat

def position(t):
    if t <= 0:
        return t
    if t <= ramp:
        return t + (stretch-1)*t*t/(2*ramp)
    return ramp*(1+stretch)/2 + (t-ramp)*stretch

old_end = (len(segment)-head)/SR
pairs = [(0,0),(head,head)]
for i in range(1,int(old_end/beat)+1):
    t=i*beat
    pairs.append((head+n(t),head+n(position(t))))
pairs.append((len(segment),head+n(position(old_end))))
mapping = here/'Time map.txt'
mapping.write_text(''.join(f'{a} {b}\n' for a,b in pairs))
subprocess.run(['rubberband','-3','--centre-focus','-M',str(mapping),'-D',
                str(pairs[-1][1]/SR),str(dry_in),str(dry_out)],check=True,
               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
stretched = load(dry_out)
target = pairs[-1][1]
stretched = np.pad(stretched,((0,max(0,target-len(stretched))),(0,0)))[:target]
assert np.isfinite(stretched).all()

# A filtered, pre-delayed stereo send leaves the drums and lead clear.
# The return comes forward when the piano outro starts.
extra = n(1.12)
dry = np.pad(stretched,((0,extra),(0,0)))
predelay = n(.024)
send = np.pad(dry[:-predelay],((predelay,0),(0,0)))
send = filt(filt(send,'highpass',310),'lowpass',6600)
reverb = Reverb(room_size=.79,damping=.48,wet_level=1,dry_level=0,width=.97)
wet = reverb(send.T,SR).T
wet = filt(filt(wet,'highpass',300),'lowpass',6700)
outro = head+n(position((outro_at-chorus_at)/SR))

def rms(x):
    return np.sqrt(np.mean(x*x))

def match_region(a,b,level):
    return db(level)*rms(dry[a:b])/max(rms(wet[a:b]),1e-9)

chorus_gain = match_region(head+n(1.25),outro-n(.4),-14.3)
outro_gain = match_region(outro+n(1.5),outro+n(9),-9.7)
t = np.arange(len(dry))/SR
weight = np.interp(t,[0,head/SR,.86,outro/SR-.28,outro/SR+1.25],
                   [0,0,chorus_gain,chorus_gain,outro_gain])[:,None]
section = dry+fade(wet*weight,0,.38)
# Only the undisturbed pre-roll is crossfaded into the slower section.
blend=n(.056)
start=chorus_at-head
section[:blend] = fade(mix[start:start+blend],0,blend/SR)+fade(section[:blend],blend/SR,0)
result=np.concatenate((mix[:start],section))
wav=here/'Slow and Reverbed premaster.wav'
sf.write(wav,result,SR,'FLOAT')

# Use the same REAPER mastering settings on the complete alternate.
header,*tracks = re.split(r'(?m)(?=^  <TRACK )',reference)
track=next(t for t in tracks if '    NAME "Runaway | Instrumental"' in t)
assert track.count('    <ITEM\n')==1
track=re.sub(r'(?m)^      POSITION .*$', '      POSITION 0',track)
track=re.sub(r'(?m)^      LENGTH .*$',f'      LENGTH {len(result)/SR:.12f}',track)
track=re.sub(r'(?m)^        FILE .*$',f'        FILE "{wav}"',track)
track=re.sub(r'(?m)^(    +NAME )"[^"]+"$',r'\g<1>"Slow and Reverbed premaster"',track)
render=alternates/'Blame Me for Everything - Slow and Reverbed.mp3'
header=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{render}"',header)
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {len(result)/SR:.12f} 0 1000',header)
header=header.replace('TAG ID3:TIT2 "Blame Me for Everything"', 'TAG ID3:TIT2 "Blame Me for Everything (Slow and Reverbed)"')
(here/'Render.rpp').write_text(header+track+'>\n')
report={'slowdown_starts':chorus_at/SR,'final_tempo':slow,'outro_starts':(start+outro)/SR,
        'duration':len(result)/SR,'chorus_wet_to_dry_db':-14.3,'outro_wet_to_dry_db':-9.7,
        'pitch_shift_semitones':0}
(here/'edit-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
