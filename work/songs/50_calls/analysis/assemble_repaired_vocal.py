"""Keep the original rendered verse between the two repaired passages."""
from pathlib import Path

import numpy as np
import soundfile as sf

session = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/50 Calls Interlude'
render = session/'Renders'
original, rate = sf.read(render/'Repaired Kanye.wav',dtype='float64')
clean, clean_rate = sf.read(render/'Clean Voice Stems/Kanye West _ Verse.wav',dtype='float64')
assert original.shape == clean.shape and rate == clean_rate == 44100

def blend(start, full, hold, end):
    left,right = round(start*rate),round(end*rate)
    t = np.arange(left,right)/rate
    w = np.interp(t,[start,full,hold,end],[0,1,1,0])
    w = (.5-.5*np.cos(np.pi*w))[:,None]
    original[left:right] += (clean[left:right]-original[left:right])*w

blend(30.26,30.35,31.425,31.485)
blend(53.04,53.10,54.26,54.37)
sf.write(session/'Media/Kanye verse repaired.wav',
         original[round(30.25*rate):round(54.6*rate)],rate,subtype='PCM_24')
