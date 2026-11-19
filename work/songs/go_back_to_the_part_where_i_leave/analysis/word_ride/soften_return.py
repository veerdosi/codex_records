"""Carry the previous bass and drum pocket while the returning harmony fades in."""
import json
from pathlib import Path
import re

import numpy as np
from scipy import signal
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
project = root/'reaper/Go Back to the Part Where I Leave'
prev = stage.parent/'pickup_cleanup'
grid = json.loads((prev/'spaced_grid.json').read_text())
join, downbeat = grid['gaps'][1]
beat = 60/87
filename = 'Runaway - extended handoffs.wav'
new_name = 'Runaway - softened harmony return.wav'
bed, sr = sf.read(project/'Media'/filename, dtype='float32')
assert sr == 44100
base = 16.551088435374
frame = lambda seconds: round((seconds-base)*sr)
start, end = frame(join-.14), frame(downbeat)
offset = frame(join-4*beat)-frame(join)
incoming = bed[start:end].copy()
outgoing = bed[start+offset:end+offset].copy()
times = (np.arange(len(incoming)) + start - frame(join))/sr

def curve(points):
    return np.interp(times, *np.asarray(points).T).astype(np.float32)[:,None]

def lowpass(audio, hz):
    kernel = signal.firwin(641, hz, fs=sr)
    return signal.fftconvolve(audio, kernel[:,None], mode='same', axes=0).astype(np.float32)

# A complementary split keeps the source identical where all bands
# reach unity. The E chord enters first above the bass, then the E bass
# takes over at the next beat. The drum band has its own shorter blend.
in_low, out_low = [lowpass(x,175) for x in [incoming,outgoing]]
in_mid, out_mid = [lowpass(x,4150)-low for x,low in [(incoming,in_low),(outgoing,out_low)]]
in_hi, out_hi = incoming-in_low-in_mid, outgoing-out_low-out_mid
low = curve([(-.14,0),(beat-.045,0),(beat+.064,1),(2*beat,1)])
mid = curve([(-.14,0),(.035,0),(.26,.22),(.58,.62),(.94,1),(2*beat,1)])
high = curve([(-.14,0),(-.01,.18),(.17,.71),(.48,1),(2*beat,1)])
joined = (out_low+(in_low-out_low)*low +
          out_mid+(in_mid-out_mid)*mid +
          out_hi+(in_hi-out_hi)*high)
fade_from_existing = curve([(-.14,0),(-.075,.38),(-.014,1),(2*beat,1)])
incoming_final = incoming+(joined-incoming)*fade_from_existing
keep_last = round(.018*sr)
incoming_final[-keep_last:] = incoming[-keep_last:]
bed[start:end] = incoming_final
assert np.isfinite(bed).all()
sf.write(stage/'Media'/new_name, bed, sr, 'FLOAT')

text = (project/f'{project.name}.rpp').read_text()
assert text.count(f'Media/{filename}')==1
text = re.sub(r'(?<=FILE ")Media/', str(project/'Media')+'/',text)
text = text.replace(str(project/'Media'/filename),str(stage/'Media'/new_name))
(stage/'Word and harmony edit.rpp').write_text(text)
