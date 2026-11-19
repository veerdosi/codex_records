"""Correct held notes in the Savage lead without moving its entrances."""
from pathlib import Path
import json
import subprocess
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.signal import correlate, correlation_lags, resample_poly

here = Path(__file__).resolve().parent
root = here.parents[4]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, fade, filt, load

current = load(root/'reaper/When You Leave/Media/21 Savage - Creepin.wav')
# Keep the complete line ending in "phone". The next bar overlaps the
# incoming singer in the source, including around the end of the last line.
length = round(30.015*SR)
dry = fade(current[:length],0,.105)
rate,hop = 16000,160
analysis = resample_poly(dry.mean(axis=1),160,441)
f0,voiced,prob = librosa.pyin(analysis,sr=rate,fmin=73,fmax=247,
                             frame_length=1024,hop_length=hop,
                             fill_na=np.nan)
midi = librosa.hz_to_midi(f0)
valid = voiced & (prob>.36) & np.isfinite(midi)
# Find stable centers and skip unvoiced consonants and pitch slides.
scale = np.array([n for n in range(37,61) if n%12 in {1,3,4,6,8,9,11}])
correction = np.zeros(len(midi))
blocks = []
i = 0
while i<len(midi):
    if not valid[i]:
        i += 1
        continue
    j = i+1
    while j<len(midi) and valid[j] and abs(midi[j]-midi[j-1])<.42:
        j += 1
    if j-i>=8:
        center = np.median(midi[i:j])
        deviation = np.median(abs(midi[i:j]-center))
        if deviation<.37:
            note = scale[np.argmin(abs(scale-center))]
            amount = np.clip((note-center)*.76,-.68,.68)
            if abs(amount)>=.065:
                correction[i:j] = amount
                blocks.append([round(i*.01,2),round(j*.01,2),int(note),round(100*amount,1)])
    i = j
correction = gaussian_filter1d(correction,2.5)
with (here/'pitch-map.txt').open('w') as out:
    for index,value in enumerate(correction):
        out.write(f'{round(index*hop*SR/rate)} {value:.6f}\n')
sf.write(here/'Savage uncorrected.wav',dry,SR,'FLOAT')
subprocess.run(['rubberband','-3','-F','--centre-focus','--pitchmap',str(here/'pitch-map.txt'),
                str(here/'Savage uncorrected.wav'),str(here/'Savage corrected raw.wav')],
               check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
raw = load(here/'Savage corrected raw.wav')
# Estimate algorithm latency from consonants where the tuning is at zero.
before = filt(dry.mean(1),'highpass',1800)
after = filt(raw.mean(1),'highpass',1800)
lags = []
for t in (1.2,3.1,6.6,11.5,16,20,24.5,28):
    a = round(t*SR)
    n = 10240
    x,y = before[a:a+n],after[a:a+n]
    c = correlate(y,x,method='fft')
    lag = correlation_lags(len(y),len(x))
    keep = abs(lag)<=1024
    lags.append(int(lag[keep][np.argmax(c[keep])]))
offset = int(np.median(lags))
aligned = np.zeros_like(dry)
first = max(0,-offset)
last = min(len(aligned),len(raw)-offset)
aligned[first:last] = raw[first+offset:last+offset]
# Blend only in the tuned syllables. Direct consonants and cadence stay
# sample-aligned with the original.
envelope = np.interp(np.arange(length)/SR,np.arange(len(correction))*.01,
                     np.clip(abs(correction)*8,0,.88)).astype(np.float32)[:,None]
tuned = fade(dry+envelope*(aligned-dry),.005,.055)
sf.write(here/'Savage tuned.wav',tuned,SR,'FLOAT')
(here/'tuning.json').write_text(json.dumps({'latency_samples':offset,'measured_lags':lags,
   'corrections_start_end_midi_cents':blocks},indent=2)+'\n')
print('Tuned',len(blocks),'sustained syllables, measured lag samples',lags, 'correction',offset,flush=True)
