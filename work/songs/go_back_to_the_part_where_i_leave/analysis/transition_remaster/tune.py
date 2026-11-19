"""Print formant-preserving correction for voiced rap syllables."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

import parselmouth
import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import soundfile as sf

RATE = 44100
STEP = .01
KEY = np.array([1, 3, 4, 6, 8, 9, 11])  # E major / C-sharp minor


def pitch(x):
    mono = signal.resample_poly(x.mean(axis=1), 160, 441)
    low = signal.sosfiltfilt(signal.butter(2,1050,fs=16000,output='sos'),mono)
    track = parselmouth.Sound(low,sampling_frequency=16000).to_pitch_ac(
        time_step=STEP,pitch_floor=65,pitch_ceiling=350,silence_threshold=.025,
        voicing_threshold=.52,octave_jump_cost=.45)
    selected = track.selected_array
    f0 = np.where(selected['frequency']>0,selected['frequency'],np.nan)
    return f0,selected['strength'],track.xs()


def align_zero_shift(raw, revised, correction, frames):
    # Consonants with zero correction provide a stable latency reference.
    offsets = []
    for t in range(1, len(raw)//RATE-1):
        c = np.argmin(abs(frames-t*RATE))
        if np.max(abs(correction[max(0,c-4):c+5]))>.08:
            continue
        a, b = round((t-.055)*RATE), round((t+.055)*RATE)
        w = raw[a:b].mean(axis=1)
        z = revised[a-2205:b+2205].mean(axis=1)
        if np.max(abs(w))<.004 or len(z)!=len(w)+4410:
            continue
        v = signal.correlate(z,w,mode='valid',method='fft')
        k = np.argmax(v)
        match = v[k]/max(1e-8,np.linalg.norm(w)*np.linalg.norm(z[k:k+len(w)]))
        if match>.76:
            offsets.append(k-2205)
    offset = int(np.median(offsets)) if offsets else 0
    index = np.arange(len(raw))+offset
    return revised[np.clip(index,0,len(revised)-1)], offset


def tune(raw, correction_path):
    f0, strength, times = pitch(raw)
    notes = 69+12*np.log2(f0/440)
    targets = np.array([i for i in range(34,68) if i%12 in KEY])
    nearest = targets[np.argmin(abs(np.nan_to_num(notes)[:,None]-targets[None,:]),axis=1)]
    cents = nearest-notes
    valid = (strength>.60) & np.isfinite(notes) & (abs(cents)<.82)
    # A sustained vowel can move toward a scale tone. Breaths, plosives
    # and fast slides keep the input samples around the correction.
    stable = np.r_[False, (nearest[1:]==nearest[:-1]) & valid[1:] & valid[:-1]]
    stable |= np.r_[stable[1:],False]
    shift = gaussian_filter1d(np.where(valid & stable,np.clip(.79*cents,-.56,.56),0),1.30)
    frames = np.rint(times*RATE).astype(int)
    frames = np.r_[0,frames,len(raw)-1]
    shift = np.r_[0,shift,0]
    shift[frames>=len(raw)-1]=0
    correction_path.write_text(''.join(f'{a} {b:.6f}\n' for a,b in zip(frames,shift) if a<len(raw)))
    with TemporaryDirectory(prefix='veer-pitch-') as directory:
        # R3 reads the realtime pitch map ahead of the output by about
        # 80 ms at this sample rate. Compensate to target the vowel itself.
        engine_map = Path(directory)/'engine_map.txt'
        compensated = np.interp(frames-round(.080*RATE),frames,shift,left=0)
        engine_map.write_text(''.join(f'{a} {b:.6f}\n' for a,b in zip(frames,compensated)))
        src, dest = (Path(directory)/f'{name}.wav' for name in ('dry','tuned'))
        sf.write(src,raw,RATE,'FLOAT')
        subprocess.run(['rubberband','-q','-3','-F','--centre-focus','--pitchmap',
                        str(engine_map),str(src),str(dest)],check=True)
        revised,_=sf.read(dest,dtype='float32',always_2d=True)
    revised, offset=align_zero_shift(raw,revised,shift,frames)
    blend = np.interp(np.arange(len(raw)),frames,np.clip(abs(shift)*31,0,1)).astype(np.float32)
    out=raw+(revised-raw)*blend[:,None]
    active=abs(shift)>.075
    assert np.any(active) and out.shape==raw.shape
    return out, {'correction_seconds':round(float(active.sum()*STEP),2),
                 'median_applied_cents':round(float(np.median(abs(shift[active]))*100),1),
                 'maximum_applied_cents':round(float(np.max(abs(shift))*100),1),
                 'rubberband_offset_samples':offset}
