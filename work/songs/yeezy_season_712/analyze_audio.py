from pathlib import Path
import numpy as np
from scipy import signal
import librosa, soxr, soundfile as sf

root = Path(__file__).resolve().parent
for p in sorted(list((root / "sources").glob("*.wav")) + list((root / "refs").glob("*.wav"))):
    audio, rate = sf.read(p, dtype="float32", always_2d=True)
    sr = 16000
    y = soxr.resample(audio.mean(1), rate, sr)
    hop = 80
    h = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, n_fft=1024)
    ac = signal.correlate(h-h.mean(), h-h.mean(), method="fft")[len(h)-1:]
    peaks = signal.find_peaks(ac[60:220])[0] + 60
    tempo = sorted([(round(60*sr/(i*hop),2),round(ac[i]/ac[0],3)) for i in peaks],key=lambda pair:-pair[1])[:6]
    low = signal.sosfilt(signal.butter(4, [30,125], "bandpass", fs=sr, output="sos"), y)
    low_h = np.sqrt(np.mean(low[:len(low)//hop*hop].reshape(-1,hop)**2,axis=1))
    print(p.stem,'duration',round(len(y)/sr,2),'pulse candidates',tempo,flush=True)
    print('10 second full/sub dBFS',[(int(i/sr),
           round(20*np.log10(np.sqrt(np.mean(y[i:i+sr*10]**2))+1e-8),1),
           round(20*np.log10(np.sqrt(np.mean(low[i:i+sr*10]**2))+1e-8),1))
          for i in range(0,len(y)-sr,sr*10)],flush=True)
    if p.parent.name=='sources':
        for a,b in [(7,32),(32,60),(60,90),(90,120)]:
            sl=h[a*sr//hop:b*sr//hop]
            if not len(sl): continue
            ac=signal.correlate(sl-sl.mean(),sl-sl.mean(),method="fft")[len(sl)-1:]
            peaks=signal.find_peaks(ac[60:220])[0]+60
            candidates=sorted([(round(60*sr/(i*hop),2),round(ac[i]/ac[0],2)) for i in peaks],key=lambda pair:-pair[1])[:5]
            print(a,b,candidates,flush=True)
        np.savez(root/(p.stem+"_rhythm.npz"),onsets=h,sub=low_h,frame_hz=sr/hop)
