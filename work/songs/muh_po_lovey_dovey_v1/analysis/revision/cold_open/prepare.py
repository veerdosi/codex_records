"""Build a short room swell from the same vocal that opens the song."""
from pathlib import Path
import sys
import numpy as np
from pedalboard import HighpassFilter, LowpassFilter, Pedalboard, Reverb
import soundfile as sf

media = Path(sys.argv[1])
with sf.SoundFile(media / 'Farebi - chorus.wav') as audio:
    rate = audio.samplerate
    audio.seek(round(55.55 * rate))
    voice = audio.read(round(.265 * rate),dtype='float32')
source = np.pad(voice,((0,round(1.135*rate)),(0,0)))
effect = Pedalboard([
    HighpassFilter(375),
    LowpassFilter(3300),
    Reverb(room_size=.58,damping=.66,wet_level=1,dry_level=0,width=.93),
])
swell = effect(source.T,rate).T[::-1].copy()
time = np.arange(len(swell))/rate
fade_in = np.minimum(1,time/.24)
fade_out = np.minimum(1,(1.4-time)/.14)
swell *= (fade_in*fade_out)[:,None]
swell *= .17/max(np.max(np.abs(swell)),1e-9)
sf.write(media/'Veer - vocal room.wav',swell,rate,subtype='PCM_24')
