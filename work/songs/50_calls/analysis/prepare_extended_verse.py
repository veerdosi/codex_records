from pathlib import Path
import shutil

import numpy as np
from scipy.signal import butter, istft, sosfiltfilt, stft
import soundfile as sf

root = Path(__file__).resolve().parents[1]
media = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/50 Calls/Media'
extension = root / 'stems/demucs/htdemucs/juice_extension'

def load(path):
    audio, rate = sf.read(path, dtype='float32', always_2d=True)
    if rate != 44100:
        raise ValueError(f'Unexpected sample rate in {path}')
    return audio

rate = 44100
extension_offset = 23 * rate  # The two backing excerpts start at 46 and 69 seconds.
crossfade_start = round(26.5 * rate)
crossfade_end = round(27.5 * rate)
weight = (.5 - .5 * np.cos(np.linspace(0, np.pi, crossfade_end - crossfade_start)))[:, None]
for label, old, new in [
    ('Drums', 'Verse-Drums.wav', 'drums.wav'),
    ('Bass', 'Verse-Bass.wav', 'bass.wav'),
    ('Guitar', 'Verse-Guitar-clean.wav', 'other.wav'),
]:
    first = load(media / old)
    second = load(extension / new)
    aligned = second[crossfade_start-extension_offset:crossfade_end-extension_offset]
    overlap = first[crossfade_start:crossfade_end]
    blend = overlap * (1 - weight) + aligned * weight
    combined = np.concatenate((first[:crossfade_start], blend, second[crossfade_end-extension_offset:]))
    print(label, 'overlap correlation', round(float(np.corrcoef(overlap.ravel(), aligned.ravel())[0,1]), 3))
    sf.write(media / f'Verse-Long-{label}.wav', combined, rate, subtype='PCM_24')

hook_start = round(24.192 * rate)
drums = load(media / 'Hook-Drums.wav')[hook_start:hook_start + 12 * rate]
percussion = sosfiltfilt(butter(3, 1850, fs=rate, btype='highpass', output='sos'), drums, axis=0)
sf.write(media / 'Verse-Percussion.wav', percussion, rate, subtype='PCM_24')

shutil.copyfile(root / 'stems/ye_extended_vocals.wav', media / 'Kanye-verse-extended.wav')

# The next singer overlaps the final voiced part of Kanye's last word.
# Attenuate the response's rising harmonics only in that overlap.
audio = load(media / 'Kanye-verse.wav')
start, end = round(28.0 * rate), round(29.1 * rate)
block = audio[start:end]
f, t, spectrum = stft(block, fs=rate, nperseg=3072, noverlap=2688, nfft=8192, axis=0)
t += start / rate
guest_pitch = np.interp(t, [28.50,28.535,28.56,28.585,28.61,28.635,28.68],
                        [257,249,237,232,230,230,234])
lead_pitch = np.interp(t,[28.50,28.535,28.56,28.585,28.61,28.635,28.66],
                       [185,178,174,172,168,156,137])
weight = np.interp(t, [28.0,28.502,28.542,28.65,28.72,29.1], [0,0,.99,.99,0,0])
distance = np.min(np.abs(f[:,None,None] - guest_pitch[None,:,None]*np.arange(1,33)), axis=2)
lead_distance = np.min(np.abs(f[:,None,None] - lead_pitch[None,:,None]*np.arange(1,36)), axis=2)
guest_width = 13 + .011 * f
stopband = 12 + .005 * f
protect = .20 + .80 * np.clip((lead_distance - 5) / 26, 0, 1)
notch = np.exp(-.5 * (np.maximum(distance - stopband[:,None], 0) / guest_width[:,None])**2)
mask = 1 - weight[None,:] * protect * notch
_, filtered = istft(spectrum * mask[:,None,:], fs=rate, nperseg=3072, noverlap=2688,
                    nfft=8192, freq_axis=0, time_axis=2)
audio[start:end] = filtered.T[:len(block)]
sf.write(media / 'Kanye-verse-tail.wav', audio, rate, subtype='PCM_24')
