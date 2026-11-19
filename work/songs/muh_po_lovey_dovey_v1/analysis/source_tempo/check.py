"""Compare ramp grid alignment against the old premaster's exact song timing."""
from pathlib import Path
import json
import numpy as np
from scipy.signal import butter, correlate, sosfiltfilt
import soundfile as sf

stage = Path(__file__).resolve().parent
old, sr = sf.read(stage/'Original premaster.wav',dtype='float32')
new, rate = sf.read(stage/'Revised premaster.wav',dtype='float32')
assert sr == rate == 48000
clock = json.loads((stage/'tempo.json').read_text())
assert np.isfinite(new).all()
at=0
for (a,bpm,ramp),(b,next_bpm,_) in zip(clock,clock[1:]):
    pace = (bpm+next_bpm)/2 if ramp else bpm
    length = (b-a)*80/pace
    if not ramp:
        if bpm == 80:
            old_a = round((a+.75)*sr)
            new_a = round((at+.75)*sr)
            size = round((b-a-1.5)*sr)
            x = old[old_a:old_a+size:7].ravel()
            y = new[new_a:new_a+size:7].ravel()
            correlation=float(np.corrcoef(x,y)[0,1])
            assert correlation > .99999,correlation
            print(f'Native rap section {at:.3f}–{at+length:.3f}, correlation {correlation:.9f}')
        at+=length
        continue
    # 10 ms windows of low-band drum envelope around the source subdivisions.
    def envelope(signal,start,duration,pad=.11):
        x=signal[round((start-pad)*sr):round((start+duration+pad)*sr)].mean(1)
        filt=sosfiltfilt(butter(2,[42,155],fs=sr,btype='bandpass',output='sos'),x)
        return np.sqrt(np.mean(filt[:len(filt)//48*48].reshape(-1,48)**2,axis=1))
    slope=(next_bpm-bpm)/length
    s0=envelope(old,a,b-a)
    s1=envelope(new,at,length)
    t=np.arange(len(s1))/1000-.11
    source_bars=(bpm*t+slope*t*t/2)/80
    guide=np.interp((source_bars+.11)*1000,np.arange(len(s0)),s0)
    values=[]
    for position in np.arange(.20,length-.12,.20):
        i=round((position+.11)*1000)
        y=guide[i-60:i+60]
        x=s1[i-80:i+80]
        if len(x)!=160 or np.std(y)<.014: continue
        c=correlate(x,y-y.mean(),mode='valid')
        den=np.sqrt(np.convolve(x*x,np.ones(len(y)),'valid')-np.convolve(x,np.ones(len(y)),'valid')**2/len(y))
        q=c/np.maximum(den*np.linalg.norm(y-y.mean()),1e-8)
        if q.max()>.65: values.append(int(q.argmax())-20)
    assert len(values)>=3,values
    print(f'Tempo ramp {at:.3f}–{at+length:.3f}, {len(values)} drum-envelope comparisons, median {np.median(np.abs(values)):.1f} ms, max {max(map(abs,values))} ms')
    at+=length
print(f'Revised duration {len(new)/sr:.3f} seconds')
assert abs(len(new)/sr-at)<.001
