"""Isolate the lead in the last overlapping fraction of the word 'leave'."""
from pathlib import Path

import numpy as np
from scipy.linalg import lstsq
import soundfile as sf

root = Path(__file__).resolve().parents[1]
workspace = root.parents[2]
media = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/50 Calls Interlude/Media'
prior, rate = sf.read(media / 'Kanye-verse-tail.wav', dtype='float64')
raw, raw_rate = sf.read(workspace / 'reaper/50 Calls/Media/Kanye-verse.wav', dtype='float64')
assert rate == raw_rate == 44100 and prior.shape == raw.shape

start, end = [round(t*rate) for t in (28.43,28.73)]
time = np.arange(start,end)/rate
block = raw[start:end]
lead_pitch = np.interp(time,
    [28.43,28.46,28.485,28.51,28.535,28.56,28.585,28.61,28.635,28.66,28.73],
    [202,196.5,189.8,183,177.6,173.6,172.3,168.2,156.1,137.3,137.3])
other_pitch = np.interp(time,
    [28.43,28.50,28.52,28.535,28.56,28.585,28.61,28.635,28.66,28.73],
    [257,257,254,249,236.9,231.5,230.1,230.1,232.8,233.5])

def partials(pitch, count):
    cycles = np.cumsum(pitch)/rate
    phase = 2*np.pi*cycles[:,None]*np.arange(1,count+1)
    return np.column_stack((np.sin(phase),np.cos(phase)))

lead = partials(lead_pitch,24)
other = partials(other_pitch,20)
design = np.column_stack((lead,other))
filtered = np.zeros_like(block)
weights = np.zeros(len(block))
width = round(.038*rate)
window = np.hanning(width)
weighted = np.sqrt(window)[:,None]
for position in range(0,len(block)-width+1,round(.003*rate)):
    section = slice(position,position+width)
    samples = design[section]
    coefficients, *_ = lstsq(samples*weighted,block[section]*weighted,
                              cond=1e-3,lapack_driver='gelsy')
    filtered[section] += (lead[section] @ coefficients[:lead.shape[1]]) * window[:,None]
    weights[section] += window
filtered /= np.maximum(weights[:,None],1e-10)

# Crossfade before the next voice becomes audible. The edit stays within
# the last syllable, and the take keeps its existing end and fade.
blend = np.interp(time,[28.43,28.483,28.526,28.695,28.72],[0,0,1,1,0])
prior[start:end] = prior[start:end]*(1-blend[:,None])+filtered*blend[:,None]
sf.write(media / 'Kanye-verse-isolated-tail.wav',prior,rate,subtype='PCM_24')
