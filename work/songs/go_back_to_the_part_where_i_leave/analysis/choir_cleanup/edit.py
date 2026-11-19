"""Remove the voiced swell before Kanye while retaining the rhythm bed."""
from pathlib import Path
import re

import numpy as np
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
project = root / 'reaper/Go Back to the Part Where I Leave'
media = project / 'Media'
name = 'Runaway - softened return attack.wav'
replacement = 'Runaway - clean verse entrance.wav'
origin = 16.551088435374
path = project/(project.name+'.rpp')
document = path.read_text()
bed, sr = sf.read(media/name,dtype='float32')
assert sr == 44100

with np.load(stage/'Stems around return.npz') as f:
    drums, bass, instruments, vocals = f['stems'][0]
    start = float(f['start'])

def n(t):
    return round((t-origin)*sr)

x = bed[n(start):n(start)+len(instruments)]
time = start+np.arange(len(x))/sr

def smooth(xpos, points):
    result = np.zeros_like(xpos)
    for (a,x), (b,y) in zip(points, points[1:]):
        u = (xpos>=a)&(xpos<b)
        c = (xpos[u]-a)/(b-a)
        result[u] = x+(y-x)*(.5-.5*np.cos(np.pi*c))
    return result[:,None]

# The swell lives mainly at the E4 fundamental and its narrow
# overtones in the instrumental stem. The drum and bass estimates
# are excluded from these notches, including on the returning downbeat.
tonal = instruments+(x-drums-bass-instruments-vocals)
voicing = sum(
    sosfiltfilt(butter(3,[low,high],fs=sr,btype='bandpass',output='sos'),tonal,axis=0)
    for low,high in [(311,349),(642,680),(974,1006),(1278,1358),(1940,2001),(3904,4015)]
)
swelled = smooth(time,[(131.54,0),(131.66,.98),(132.39,.98),(132.54,0)])
# Reject the separate, quieter voice bleed on the backing at the
# entrance. Kanye's lead is on its own track and is never processed here.
bleed = smooth(time,[(132.25,0),(132.41,1),(133.10,1),(133.32,0)])
updated = x - swelled * voicing - bleed * vocals
x[:] = updated

sf.write(stage/replacement,bed,sr,'FLOAT')
assert document.count(name)==1
revised = document.replace(name,replacement)
(stage/'Portable edit.rpp').write_text(revised)

for label,text,wav in [
    ('Original premaster',document,True),
    ('Revised premaster',revised,True),
    ('Revised master',revised,False),
]:
    text=text.replace(f'FILE "Media/{replacement}"',f'FILE "{stage/replacement}"')
    text=text.replace('FILE "Media/',f'FILE "{media}/')
    ext='wav' if wav else 'mp3'
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
