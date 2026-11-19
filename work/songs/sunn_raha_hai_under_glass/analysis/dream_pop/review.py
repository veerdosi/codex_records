"""Review aligned REAPER renders, harmony and attack timing."""
from pathlib import Path
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfilt
import soundfile as sf

P = Path(__file__).resolve().parent
OLD = P.parent/'vocal_phrasing'
SHOEGAZE = '--shoegaze' in sys.argv
RATE = 44100
BEAT = 60/85.42


def read(path):
    data, rate = sf.read(path, dtype='float32', always_2d=True)
    assert rate == RATE and np.isfinite(data).all(), path
    return data


def db(x):
    return 10*np.log10(np.maximum(1e-12, np.mean(x*x)))


def band(x, low, high):
    return sosfilt(butter(2,[low,high],btype='bandpass',fs=RATE,output='sos'),x,axis=0)


def crop(x,a,b):
    return x[round(a*RATE):round(b*RATE)]


def trace(x, low, high):
    x = band(x, low,high)
    hop = round(.05*RATE)
    frames = x[:len(x)//hop*hop].reshape(-1,hop,2)
    return 10*np.log10(np.maximum(1e-10,np.mean(frames**2,axis=(1,2))))


premaster = read(P/('Premaster.wav' if not SHOEGAZE else 'Shoegaze premaster.wav'))
backing = read(P/('Backing.wav' if not SHOEGAZE else 'Shoegaze backing.wav'))
oldmix = read(OLD/'Premaster.wav')
oldback = read(OLD/'Backing.wav')
lead = read(P.parent/'shoegaze/Voice.wav')
guitars = read(P/('Guitars.wav' if not SHOEGAZE else 'Shoegaze guitars.wav'))
bed = read(P/('Rhythm.wav' if not SHOEGAZE else 'Shoegaze rhythm.wav'))
old_bed = read(P/'Before rhythm.wav')
assert premaster.shape == oldmix.shape == backing.shape == lead.shape
residual = float(np.max(np.abs((premaster-backing) - lead)))
assert residual < 2e-5, residual
assert np.max(abs(premaster)) < 1
windows = [('Intro',0,11.21),('Verse',11.24,33.71),
           ('Verse rise',33.71,50.57),('Prechorus',50.57,84.28),
           ('First refrain',84.29,94.12),('Interlude',94.12,102.55),
           ('Verse 2',102.55,122.22),('Lift',122.22,150.31),
           ('Last refrain',150.32,171.38),('Outro',171.39,182.06)]
results = []
for name,a,b in windows:
    prev,curr = crop(oldmix,a,b),crop(premaster,a,b)
    gain_db = db(prev)-db(curr)
    lo,hi = 980,3300
    l = band(crop(lead,a,b),lo,hi)
    ob = band(crop(oldback,a,b),lo,hi)
    nb = band(crop(backing,a,b),lo,hi)
    hop = round(.05*RATE)
    n = len(l)//hop*hop
    vocal_power = np.mean(l[:n].reshape(-1,hop,2)**2,axis=(1,2))
    mask = vocal_power > 10**(-38/10)
    def active_db(x):
        return db(x[:n].reshape(-1,hop,2)[mask])
    result = dict(section=name, prior_mix_db=round(float(db(prev)),2),
                  revised_mix_db=round(float(db(curr)),2),
                  bass_drum_change_db=round(float(db(band(crop(bed,a,b),38,170))-db(band(crop(old_bed,a,b),38,170))),2))
    if mask.any():
        result['matched_voice_band_clearance_db'] = round(float(active_db(ob)-active_db(nb)-gain_db),2)
    results.append(result)
fig, (ax, bx) = plt.subplots(2, 1, figsize=(13,6), sharex=True, constrained_layout=True)
for signal,label in [(lead,'Shreya'),(oldback,'Previous backing'),(backing,'Revised backing'),(guitars,'Revised guitars and pads')]:
    y = trace(signal,980,3300)
    ax.plot(.025+np.arange(len(y))*.05,y,linewidth=.8,label=label)
for signal,label in [(old_bed,'Previous low end'),(bed,'Revised low end')]:
    y = trace(signal,38,170)
    bx.plot(.025+np.arange(len(y))*.05,y,linewidth=.8,label=label)
for axis in (ax,bx):
    for _,a,b in windows:
        axis.axvline(a,color='k',alpha=.13)
    axis.legend(loc='upper right')
    axis.set_ylim(-57,-12)
    axis.set_ylabel('dBFS')
bx.set_xlim(0,182)
bx.set_xlabel('Song time (seconds)')
fig.savefig(P/('Rendered contour - shoegaze.png' if SHOEGAZE else 'Rendered contour.png'),dpi=105)
print(json.dumps(dict(vocal_null_max=residual,premaster_peak_dbfs=round(float(20*np.log10(np.max(abs(premaster)))),2),
                      sections=results),indent=2))
