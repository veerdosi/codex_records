from pathlib import Path
import sys
import numpy as np
import soundfile as sf
from scipy import signal
import librosa
import subprocess, re

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parents[1] / 'shared'))
from dsp import SR, load, db, fade, stretch

def excerpt(audio, start, end):
    return audio[round(SR * start):round(SR * end)]

def loudness(audio):
    result = subprocess.run(["ffmpeg","-hide_banner","-f","f32le","-ar",str(SR),"-ac","2","-i","pipe:0","-af","ebur128","-f","null","-"], input=audio.astype("<f4").tobytes(), capture_output=True, check=True)
    return float(re.findall(rb"I:\s+(-?[\d.]+) LUFS", result.stderr)[-1])

def leveled(audio, target):
    return audio * db(target - loudness(audio))

juice = root / 'stems/demucs/htdemucs/juice_first'
drums, bass, guitar, hook = [load(juice / f'{part}.wav') for part in ('drums', 'bass', 'other', 'vocals')]
bed = drums + bass + guitar
ye = load(root / 'stems/ye_first_vocals.wav')
love = load(root / 'sources/i_love_kanye.wav')
kbar = 240 / 82
juice_downbeat = .192

for index in range(18):
    a, b = juice_downbeat + 3 * index, juice_downbeat + 3 * (index + 1)
    part = excerpt(bass, a, b)
    ac = np.abs(np.fft.rfft(part.mean(1) * np.hanning(len(part))))
    freqs = np.fft.rfftfreq(len(part), 1 / SR)
    good = (freqs > 30) & (freqs < 180)
    main = freqs[good][np.argmax(ac[good])]
    pitch = librosa.hz_to_note(main) if np.max(abs(part)) > .003 else '–'
    print(f'bar {index:02d} {a:6.3f} bass {pitch:3s}', *(f'{loudness(excerpt(t,a,b)):6.1f}' for t in (drums,bass,guitar,hook)))

# Use the same 80 BPM drum and guitar segment for all candidates.
duration = 12
base = leveled(excerpt(bed, 48.192, 57.0), -20)
base = np.concatenate((base, leveled(excerpt(bed, 39.0, 42.192), -20)))
context = leveled(excerpt(bed + hook, 42.192, 48.192), -16.7)
for name, audio, start, end, position, rate in [
    ('wouldnt_leave_first', ye, 16.89, 28.51, (33.89-32.52)/(80/82), 80/82),
    ('i_love_kanye', love, .0, 12.33, 0.0, 1.0),
    ('wouldnt_leave_second', load(root/'stems/demucs/htdemucs/ye_middle/vocals.wav'), 2.48, 14.4, -.08, 80/82),
]:
    take = excerpt(audio, start, end)
    voice = leveled(fade(stretch(take, len(take)/SR/rate, name), .026, .09), -17)
    mix = np.zeros((round(SR*14),2), dtype='float32')
    mix[:len(base)] = fade(base, .024, .18)
    offset = round(position*SR)
    if offset < 0:
        voice = voice[-offset:]
        offset = 0
    mix[offset:offset+len(voice)] += voice
    preview = np.concatenate((fade(context, .085, .025), mix))
    sf.write(root / 'previews' / f'{name}.wav', leveled(preview,-16), SR, subtype='PCM_24')
