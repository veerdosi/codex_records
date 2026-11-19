"""Reconstruct the backing at the first hook exit for a per-track level check."""
from pathlib import Path
import re
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PROJECT = ROOT / 'reaper/Blame Me for Everything'
RATE = 44100
START = 57
END = 69


def sample(seconds):
    return round(float(seconds) * RATE)


def read_tracks(path, extra_media=None, *, backing_only=False):
    times = np.arange(sample(START), sample(END)) / RATE
    tracks = {}
    for block in re.split(r'(?m)(?=^  <TRACK )', path.read_text())[1:]:
        name = re.search(r'(?m)^    NAME "([^"]+)"', block)[1]
        if backing_only and is_vocal(name):
            continue
        signal = np.zeros((len(times), 2), dtype=np.float32)
        for item in block.split('    <ITEM\n')[1:]:
            value = lambda k: re.search(rf'(?m)^      {k} (\S+)', item)[1]
            position, length, offset = [sample(value(k)) for k in ('POSITION', 'LENGTH', 'SOFFS')]
            start = max(position, sample(START))
            end = min(position + length, sample(END))
            if end <= start:
                continue
            filename = Path(re.search(r'(?m)^        FILE "([^"]+)"', item)[1])
            path = PROJECT / filename
            if extra_media and (extra_media / filename.name).is_file():
                path = extra_media / filename.name
            with sf.SoundFile(path) as source:
                assert source.samplerate == RATE
                source.seek(offset + start - position)
                signal[start - sample(START):end - sample(START)] += source.read(end - start, dtype='float32', always_2d=True)
        envelope = re.search(r'(?ms)^    <VOLENV3\n(.*?)^    >', block)
        if envelope:
            points = np.asarray(re.findall(r'(?m)^      PT (\S+) (\S+) 0$', envelope[1]), dtype=float)
            signal *= np.interp(times, points[:, 0], points[:, 1])[:, None]
        tracks[name] = signal
    return tracks


def is_vocal(name):
    return name.startswith(('Kanye West |', '21 Savage |'))


def rms(x):
    return 10 * np.log10(max(np.mean(x*x), 1e-12))


def between(x, a, b):
    return x[sample(a-START):sample(b-START)]


def band(x, cutoff, kind):
    return sosfiltfilt(butter(2, cutoff, fs=RATE, btype=kind, output='sos'), x, axis=0)


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / 'Blame Me for Everything.rpp'
    tracks = read_tracks(path, HERE / 'Media' if len(sys.argv) > 1 else None)
    backing = sum(value for name, value in tracks.items() if not is_vocal(name))
    windows = [(59,59.4),(59.4,59.8),(59.8,60.2),(60.2,60.6),(60.6,61),(61,61.4),
               (61.4,61.8),(61.8,62.2),(62.2,62.6),(62.6,63),(63,63.4),(63.4,63.8),
               (63.8,64.2),(64.2,64.6),(64.6,65),(65,65.4),(65.4,65.8),(65.8,66.2)]
    print('Track                               ', ' '.join(f'{a:5.1f}' for a,_ in windows))
    for name, x in [('Backing sum',backing), ('Backing < 150 Hz',band(backing,150,'lowpass')),
                    ('Backing 180–4000 Hz',band(backing,[180,4000],'bandpass')), *tracks.items()]:
        if rms(x) > -65:
            print(f'{name:37s}', ' '.join(f'{rms(between(x,a,b)):5.1f}' for a,b in windows))
