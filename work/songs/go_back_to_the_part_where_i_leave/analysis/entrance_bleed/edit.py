"""Replace the entrance's contaminated tonal layer using an aligned source separation."""
from pathlib import Path
import re

import numpy as np
from scipy import signal
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
project = root/'reaper/Go Back to the Part Where I Leave'
media = project/'Media'
current = 'Runaway - clean verse entrance.wav'
updated = 'Runaway - clean verse backing.wav'
project_file = project/(project.name+'.rpp')
sr = 44100
bed, rate = sf.read(media/current,dtype='float32')
assert rate == sr
n = lambda t: round(t*sr)
origin = 16.551088435374
join = 132.41380952381002
source_offset = n(104.24-98)
at = n(join)-n(origin)
length = n(3.6)
prior = bed[at:at+length]
instrumental = sf.read(
    stage/'Runaway clean instrumental.wav',start=source_offset,frames=length,
    dtype='float32',
)[0]
voice = sf.read(stage/'Runaway all voices.wav',start=source_offset,frames=length,dtype='float32')[0]
assert len(instrumental)==length

def filt(x, op, cutoff):
    sos = signal.butter(3,cutoff,fs=sr,btype=op,output='sos')
    return signal.sosfiltfilt(sos,x,axis=0)

def rms(x):
    return np.sqrt(np.mean(x*x))

# Keep the current sub, kick body and transition curve. Fit the cleaned
# source's level from the stable low end of the bar.
low_current = filt(prior, 'lowpass', 145)
low_clean = filt(instrumental, 'lowpass', 145)
fit=slice(n(.32),len(prior))
gain = np.sum(low_current[fit]*low_clean[fit])/np.sum(low_clean[fit]**2)
assert .42 < gain < .54, gain
cor = np.corrcoef(low_current[fit].ravel(),low_clean[fit].ravel())[0,1]
assert cor > .95, cor
clean = gain*(instrumental-low_clean)
# Reduce voice-dominant residual bins during the pickup. The model's
# two stems are already complementary except for a constant gain.
fft=1536
hop=fft//4
def stft(x):
    return signal.stft(x.T,fs=sr,nperseg=fft,noverlap=fft-hop,axis=-1)
f, _, c = stft(clean)
_, _, v = stft(gain*voice)
dominant = abs(v)**2/(abs(v)**2+2.75*abs(c)**2+1e-10)
weight = np.clip((f-160)/160,0,1)*np.clip((5400-f)/1500,0,1)
c *= 1 - .72*dominant*weight[None,:,None]
_, cleaned = signal.istft(c,fs=sr,nperseg=fft,noverlap=fft-hop,time_axis=-1,freq_axis=-2)
clean = cleaned.T[:length].astype('float32')
new = low_current+clean

t=np.arange(length)/sr
w=np.clip(t/.044,0,1)*np.clip((3.6-t)/.32,0,1)
w=.5-.5*np.cos(np.pi*w)
print('matched input gain',gain,'low-band correlation',cor)
print('whole-window levels',20*np.log10(rms(prior)),20*np.log10(rms(new)))
for a,b in [(.05,.38),(.38,.8),(.8,1.4),(1.4,2.7),(2.7,3.25)]:
 section=slice(n(a),n(b))
 ref=filt(voice,'bandpass',[280,4400])[section]
 measure=lambda z: abs(np.sum(filt(z,'bandpass',[280,4400])[section]*ref))/np.sum(ref**2)
 print(a,b,'voice projection reduction, dB',round(20*np.log10((measure(new)+1e-10)/(measure(prior)+1e-10)),2))
prior[:]=prior+(new-prior)*w[:,None]
sf.write(stage/updated,bed,sr,'FLOAT')

original=project_file.read_text()
assert original.count(current)==1
revised=original.replace(current,updated)
(stage/'Portable edit.rpp').write_text(revised)
for label,text,wav in [('Original premaster',original,True),
                       ('Revised premaster',revised,True),('Revised master',revised,False)]:
    text=text.replace(f'FILE "Media/{updated}"',f'FILE "{stage/updated}"')
    text=text.replace('FILE "Media/',f'FILE "{media}/')
    ext='wav' if wav else 'mp3'
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
