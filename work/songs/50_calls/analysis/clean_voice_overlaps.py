"""Replace overlapping voices at the verse entrance and ending."""
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

song = Path(__file__).resolve().parents[1]
analysis = song/'analysis'
media = Path.home()/'Library/Application Support/REAPER/MCP Sessions/50 Calls Interlude/Media'
rate = 44100

def load(path):
    audio, sample_rate = sf.read(path,dtype='float64',always_2d=True)
    if sample_rate != rate or audio.shape[1] != 2:
        raise ValueError(f'Expected a stereo 44.1 kHz file in {path}')
    return audio

def weight(time, boundaries):
    fraction = np.interp(time,boundaries,[0,1,1,0])
    return (.5-.5*np.cos(np.pi*fraction))[:,None]

def clean_lead(original, replacement, origin, edges, output):
    vocal = load(media/original)
    isolated = load(analysis/replacement)
    start = round(origin*rate)
    end = start+len(isolated)
    time = np.arange(start,end)/rate
    blend = weight(time,edges)
    vocal[start:end] += (isolated-vocal[start:end])*blend
    sf.write(media/output,vocal,rate,subtype='PCM_24')

clean_lead('Kanye-verse-extended.wav','entry_kanye_only.wav',1.5,
           (3.84,3.925,4.92,5.12),'Kanye-verse-entry-clean.wav')
clean_lead('Kanye-verse-isolated-tail.wav','tail_kanye_only.wav',25.8,
           (27.87,27.97,28.68,28.76),'Kanye-verse-ending-clean.wav')

guitar = load(media/'Verse-Long-Guitar.wav')
drums = load(media/'Verse-Long-Drums.wav')
bass = load(media/'Verse-Long-Bass.wav')
backing = guitar+drums+bass
speech_band = butter(3,(195,6800),btype='bandpass',fs=rate,output='sos')
for part, origin, edges in [
    ('entry',51,(51.64,51.95,55.59,55.89)),
    ('tail',75,(76.74,77.02,79.97,80.29)),
]:
    separated = load(song/'stems'/f'backing_{part}_target_instrumental.wav')
    start = round((origin-46)*rate)
    end = start+len(separated)
    time = origin+np.arange(len(separated))/rate
    # Apply only the midrange correction. The bass and drum tracks stay in place.
    difference = sosfiltfilt(speech_band,separated-backing[start:end],axis=0)
    guitar[start:end] += difference*weight(time,edges)
staged = media/'Verse-Long-Guitar-clean-vocals.tmp.wav'
sf.write(staged,guitar,rate,subtype='PCM_24')
staged.replace(media/'Verse-Long-Guitar-clean-vocals.wav')
