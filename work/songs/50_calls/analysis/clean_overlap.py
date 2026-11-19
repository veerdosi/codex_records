from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

root = Path(__file__).resolve().parents[1]
media = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/50 Calls/Media'
guitar, rate = sf.read(media/'Verse-Guitar.wav', dtype='float32')
drums = sf.read(media/'Verse-Drums.wav', dtype='float32')[0]
bass = sf.read(media/'Verse-Bass.wav', dtype='float32')[0]
clean = sf.read(root/'stems/juice_verse_overlap_instrumental.wav', dtype='float32')[0]
offset = 8 * rate
backing = (guitar+drums+bass)[offset:offset+len(clean)]
difference = sosfiltfilt(butter(3,(170,7400),fs=rate,btype='bandpass',output='sos'),clean-backing,axis=0)
time = np.arange(len(clean))/rate
blend = np.interp(time,[0,2.8,3.3,6.5,7.1,10],[0,0,.85,.85,0,0])
guitar[offset:offset+len(clean)] += (difference * blend[:,None]).astype('float32')
sf.write(media/'Verse-Guitar-clean.wav',guitar,rate,subtype='PCM_24')
