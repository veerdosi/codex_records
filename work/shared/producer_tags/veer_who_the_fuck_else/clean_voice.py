"""Prepare the first AirPod take and a short reflection for the tag."""
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import butter, istft, sosfiltfilt, stft
import soundfile as sf

root = Path(__file__).resolve().parent
media = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/Veer Producer Tag Dark/Media'
audio, rate = sf.read(root / 'analysis/takes.wav', dtype='float32')
if rate != 48000 or audio.ndim != 1:
    raise ValueError('Expected a 48 kHz mono take.')

def band(x, kind, frequency):
    return sosfiltfilt(butter(2, frequency, btype=kind, fs=rate, output='sos'), x)

audio = band(audio, 'highpass', 86)
_, times, bins = stft(audio, fs=rate, nperseg=1024, noverlap=768)
noise_frames = ((times >= 2.28) & (times <= 2.77)) | ((times >= 5.53) & (times <= 6.61))
power = np.abs(bins)**2
noise = np.median(power[:,noise_frames], axis=1, keepdims=True)
gain = np.sqrt(np.clip(1 - 1.35*noise / (power+1e-12), .23, 1))
gain = gaussian_filter(gain, sigma=(.65,1.25))
_, clean = istft(bins*gain, fs=rate, nperseg=1024, noverlap=768)
clean = clean[:len(audio)]
clean = clean - .14*band(clean, 'lowpass', 310) + .43*band(clean, 'bandpass', (1450,4150))

# Keep the natural pause and the full final consonant of the first take.
take = clean[round(.457*rate):round(2.167*rate)]
with TemporaryDirectory(prefix='veer-voice-') as temporary:
    dry = Path(temporary) / 'take.wav'
    lower = Path(temporary) / 'lower.wav'
    sf.write(dry, take, rate, subtype='PCM_24')
    subprocess.run(['rubberband', '-3', '-F', '-p', '-.85', str(dry), str(lower)], check=True)
    take, _ = sf.read(lower, dtype='float32')

take *= .77 / max(abs(take).max(), .001)
sf.write(media / 'Veer first take.wav', take, rate, subtype='PCM_24')

reflection = band(take, 'bandpass', (230, 2450))
opening = round(1.1*rate)
reflection[:opening] = 0
ramp = round(.12*rate)
reflection[opening:opening+ramp] *= np.linspace(0,1,ramp)
room = np.zeros((len(take)+round(.12*rate),2),dtype=np.float32)
for channel, taps in enumerate([((.027,.073),(.063,.024)),((.039,.061),(.080,.022))]):
    for delay, gain in taps:
        offset = round(delay*rate)
        room[offset:offset+len(reflection),channel] += reflection * gain
sf.write(media / 'Short reflection.wav', room, rate, subtype='PCM_24')
