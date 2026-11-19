"""Lower Calm's final vowel at the existing syllable boundary."""
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf

media=Path(sys.argv[1])
rate=48000
source_origin=101.38
start,end=102.073,102.267
with sf.SoundFile(media/'Namastute - native vocals.wav') as voice:
    assert voice.samplerate==rate
    voice.seek(round(source_origin*rate))
    original=voice.read(round(1.22*rate),dtype='float32')
with TemporaryDirectory() as workdir:
    a,b=(Path(workdir)/f for f in ('original.wav','lowered.wav'))
    sf.write(a,original,rate,subtype='FLOAT')
    subprocess.run(['rubberband','-q','-3','-F','-p','-1.75','-t','1',str(a),str(b)],check=True)
    lowered,sr=sf.read(b,dtype='float32')
    assert sr==rate and abs(len(lowered)-len(original))<4
left,right=(round((t-source_origin)*rate) for t in (start,end))
out=original[left:right].copy()
t=np.arange(left,right)/rate+source_origin
blend=np.clip((t-102.096)/.022,0,1)
blend=(.5-.5*np.cos(blend*np.pi))[:,None]
out+=(lowered[left:right]-out)*blend
sf.write(media/'Calm - falling syllable.wav',out,rate,subtype='PCM_24')
