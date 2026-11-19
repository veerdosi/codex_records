"""Stem-aware comparison for an unmastered mix and its known backing."""
from itertools import combinations
from pathlib import Path
import argparse
import json

import numpy as np
from scipy import signal
import soundfile as sf

def db(value):
    return 20 * np.log10(max(float(value), 1e-12))

def move(x, samples):
    y = np.zeros_like(x)
    if samples > 0:
        y[samples:] = x[:-samples]
    elif samples < 0:
        y[:samples] = x[-samples:]
    else:
        y[:] = x
    return y

def read(path, start, duration):
    with sf.SoundFile(path) as f:
        sr = f.samplerate
        f.seek(round(start * sr))
        samples = f.read(round(duration * sr), dtype='float32', always_2d=True)
    if len(samples) != round(duration * sr):
        raise ValueError(f'Short audio excerpt: {path}')
    return samples, sr

def lag_and_correlation(candidate, reference, sr, search_seconds=.30):
    a = candidate.mean(axis=1, dtype=np.float64)
    b = reference.mean(axis=1, dtype=np.float64)
    a -= a.mean()
    b -= b.mean()
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-9:
        return 0, 0.
    radius = min(round(search_seconds * sr), len(a) - 1)
    mid = len(b) - 1
    scores = signal.correlate(a, b, method='fft')[mid-radius:mid+radius+1] / denom
    best = int(np.argmax(scores))
    return best - radius, float(scores[best])

def pitch_track(samples, sr):
    import librosa
    from math import gcd
    divisor = gcd(sr, 16000)
    mono = signal.resample_poly(samples.mean(axis=1), 16000//divisor, sr//divisor)
    f0, voiced, probability = librosa.pyin(mono, fmin=75, fmax=650, sr=16000,
        frame_length=1024, hop_length=160, resolution=.2, fill_na=np.nan)
    return f0, voiced & (probability > .45)

def compare(reference, candidate, sr, use_pitch=True):
    if candidate.shape != reference.shape:
        raise ValueError('Audio buffers must share length and channel count.')
    if len(reference) < sr or not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise ValueError('Provide at least one second of finite audio.')
    lag, correlation = lag_and_correlation(candidate, reference, sr)
    result = {'correlation': round(correlation, 5), 'flags': []}
    if correlation < .75:
        result['flags'] = ['unmatched']
        if use_pitch:
            a, av = pitch_track(reference, sr)
            b, bv = pitch_track(candidate, sr)
            ok = av & bv
            if ok.sum() >= 30:
                cents = 1200 * np.log2(b[ok] / a[ok])
                estimate = float(np.median(cents))
                agreement = float(np.mean(abs(cents - estimate) < 35))
                result.update(pitch_cents=round(estimate, 1), pitch_agreement=round(agreement, 3))
                if agreement > .55 and abs(estimate) > 45:
                    result['flags'] = ['pitch']
        return result
    aligned = move(candidate, -lag)
    margin = round(.32 * sr)
    x = reference[margin:-margin]
    y = aligned[margin:-margin]
    gain = float(np.sum(x*y, dtype=np.float64) / np.sum(x*x, dtype=np.float64))
    result.update(offset_samples=lag, offset_ms=round(lag*1000/sr, 2), gain_db=round(db(gain), 3), linear_gain=gain)
    if abs(lag/sr) > .012:
        result['flags'].append('timing')
    if abs(db(gain)) > 1.0:
        result['flags'].append('level')
    hop = round(.01*sr)
    n = len(x)//hop
    def rms_frames(z):
        return np.sqrt(np.mean(z[:n*hop].reshape(n,hop,-1)**2,axis=(1,2)))
    ref_rms, obs_rms = rms_frames(x), rms_frames(y)/gain
    active = ref_rms > max(.04*np.max(ref_rms), .001)
    absent = active & (obs_rms < .10*ref_rms)
    edges = np.flatnonzero(np.diff(np.r_[False, absent, False]))
    result['dropouts'] = [
        {'start_s':round((margin+a*hop+lag)/sr, 3),'duration_ms':round((b-a)*hop*1000/sr)}
        for a,b in zip(edges[::2],edges[1::2]) if (b-a)*hop/sr >= .075
    ]
    if result['dropouts']:
        result['flags'].append('dropout')
    result['residual_db'] = round(db(np.linalg.norm(y-x*gain)/np.linalg.norm(x)),2)
    return result

def repeat_map(path, starts, bpm=87.):
    # Skip one beat at each edge to avoid crossfades into different sections.
    beat = 60 / bpm
    clips = [read(path, start+beat, 30*beat) for start in starts]
    output = []
    for i,j in combinations(range(len(starts)), 2):
        x, sr = clips[i]
        y, _ = clips[j]
        lag, _ = lag_and_correlation(y, x, sr, .004)
        y = move(y, -lag)
        x = x[200:-200].reshape(-1)
        y = y[200:-200].reshape(-1)
        corr = float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)))
        output.append({'start_a_s':round(starts[i],3),'start_b_s':round(starts[j],3),
                       'waveform_correlation':round(corr,5),'align_ms':round(lag*1000/sr,3)})
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    pair = commands.add_parser('compare', help='Compare a rendered stem with a reference.')
    pair.add_argument('reference', type=Path)
    pair.add_argument('candidate', type=Path)
    pair.add_argument('--backing', type=Path, help='Subtract this sample-aligned backing from an unmastered candidate mix.')
    pair.add_argument('--skip-pitch', action='store_true')
    repeats = commands.add_parser('repeats', help='Compare eight-bar sections of an instrumental.')
    repeats.add_argument('instrumental', type=Path)
    repeats.add_argument('--bpm', type=float, required=True)
    repeats.add_argument('--starts', type=float, nargs='+', required=True, help='Section starts in seconds.')
    args = parser.parse_args()
    if args.command == 'repeats':
        if args.bpm <= 0 or len(args.starts) < 2 or min(args.starts) < 0:
            parser.error('Use positive BPM and at least two nonnegative section starts.')
        result = repeat_map(args.instrumental, args.starts, args.bpm)
    else:
        reference, rate = sf.read(args.reference, always_2d=True, dtype='float32')
        candidate, candidate_rate = sf.read(args.candidate, always_2d=True, dtype='float32')
        if rate != candidate_rate:
            parser.error('Sample rates must match.')
        if args.backing:
            backing, backing_rate = sf.read(args.backing, always_2d=True, dtype='float32')
            if backing_rate != rate or backing.shape != candidate.shape:
                parser.error('Backing and candidate must match in sample rate, duration and channels.')
            candidate -= backing
        result = compare(reference, candidate, rate, use_pitch=not args.skip_pitch)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
