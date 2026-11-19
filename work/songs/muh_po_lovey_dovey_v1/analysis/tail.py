from pathlib import Path
import numpy as np, soundfile as sf
from scipy.signal import butter,sosfilt
from pedalboard import Pedalboard,Reverb
import sys
p=Path(sys.argv[1]); sr=48000
B=240/84
end=68*B
# Use the last Farebi chord before the outro, with a tempo-locked stereo decay.
with sf.SoundFile(p/'Renders/Stems/Farebi _ Music.wav') as f:
    f.seek(round((end-.62)*sr)); src=f.read(round(.56*sr),dtype='float32')
with sf.SoundFile(p/'Renders/Stems/Farebi _ Drums.wav') as f:
    f.seek(round((end-.62)*sr)); src+=.14*f.read(len(src),dtype='float32')
src*=np.minimum(1,np.arange(len(src))/960)[:,None]
src*=np.minimum(1,np.arange(len(src))[::-1]/2500)[:,None]
src=sosfilt(butter(2,[205,3900],fs=sr,btype='bandpass',output='sos'),src,axis=0).astype('float32')
y=np.zeros((round(sr*3.2),2),dtype='float32')
# Reverb tail carries the actual final chord's overtones, without carrying a vocal.
for k,gain in enumerate([.87,.43,.23,.12,.07]):
    i=round(sr*(.10+k*(60/84)*.75))
    if i+len(src)<len(y): y[i:i+len(src)]+=src[:,::-1] * gain if k%2 else src*gain
z=Pedalboard([Reverb(room_size=.40,damping=.65,wet_level=.24,dry_level=.85,width=.92)])(y.T,sr).T
z*=np.linspace(1,0,len(z))[:,None]**1.2
sf.write(p/'Media/Farebi - chord tail.wav',z,sr,subtype='PCM_24')
