from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from pedalboard import Compressor, Pedalboard, Reverb

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from dsp import SR, db, fade, filt, load

BEAT = 60 / 95
VERSE_START = 16 * BEAT
HOOK_START = 52 * BEAT

def sample(time):
    return round(time * SR)

def cut(audio, start, end):
    return audio[sample(start):sample(end)].copy()

def body(audio):
    band = filt(audio, 'bandpass', (150, 5200))
    return float(np.sqrt(np.mean(band ** 2) + 1e-12))

def add(bus, audio, at):
    index = sample(at)
    bus[index:index + len(audio)] += audio

def room(audio):
    padded = np.pad(audio, ((0, SR), (0, 0)))
    effect = Pedalboard([Reverb(room_size=.44, damping=.74, dry_level=0,
                              wet_level=1, width=.91)])
    return filt(filt(effect(padded.T.copy(), SR).T, 'highpass', 235),
                'lowpass', 5200)

def warp(audio, ratio=1, semitones=0):
    with tempfile.TemporaryDirectory(prefix='wic-warp-') as folder:
        source, dest = (Path(folder) / name for name in ('in.wav', 'out.wav'))
        sf.write(source, audio * .5, SR, subtype='FLOAT')
        subprocess.run(['rubberband', '-q', '-3', '--centre-focus', '-t',
                        str(ratio), '-p', str(semitones), str(source), str(dest)],
                       check=True)
        result = load(dest) * 2
        assert abs(len(result) - len(audio) * ratio) < 4
        return result

def loudness(path):
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af',
                            'loudnorm=I=-14.2:TP=-1.3:LRA=8:print_format=json',
                            '-f', 'null', '-'], capture_output=True, text=True, check=True)
    import json
    return json.loads(re.findall(r'\{[^{}]+\}', result.stderr)[-1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('track')
    parser.add_argument('origin', type=float)
    parser.add_argument('bpm', type=float)
    parser.add_argument('anchor', type=float)
    parser.add_argument('start', type=float)
    parser.add_argument('end', type=float)
    parser.add_argument('--offset', type=float, default=0)
    parser.add_argument('--pitch', type=float, default=0)
    args = parser.parse_args()

    previous = load(PROJECT / 'what_it_cost_reordered.wav')
    old_vocals = load(PROJECT / 'reordered_vocal_check.wav')
    backing = load(PROJECT / 'reordered_backing_check.wav')
    original_verse = np.zeros_like(old_vocals)
    start, end = sample(VERSE_START), sample(HOOK_START)
    original_verse[start:end] = old_vocals[start:end]
    mix = previous.copy()
    new_lead = np.zeros_like(mix)
    vocal = load(HERE / f'{args.track}_cut_vocals.wav')
    verse = cut(vocal, args.start - args.origin, args.end - args.origin)
    ratio = args.bpm / 95
    verse = warp(verse, ratio, args.pitch)
    verse = filt(verse, 'highpass', 91)
    verse = Pedalboard([Compressor(threshold_db=-20, ratio=1.65,
                                  attack_ms=18, release_ms=112)])(verse.T.copy(), SR).T
    verse = fade(verse, .027, .14)
    at = VERSE_START + (args.start - args.anchor) * ratio + args.offset
    stop = at + len(verse) / SR
    assert at >= VERSE_START - .3 and stop <= HOOK_START + .22, (at, stop)
    verse *= body(cut(backing, at, stop)) * db(-2.15) / body(verse)
    add(new_lead, verse, at)
    vocal_change = new_lead - original_verse
    wet_change = fade(room(vocal_change)[:sample(34.05)], 0, .75)
    mix += vocal_change
    add(mix, wet_change * .041, 0)

    piano = load(HERE / 'coltrane.wav')
    motif = warp(cut(piano, 1.435, 3.17), 1.115, -3)
    motif = fade(filt(filt(motif, 'highpass', 125), 'lowpass', 4900), .028, .42)
    motif *= db(-21.4) / body(motif)
    t = np.arange(sample(1.9)) / SR
    level = .17 + .83 * np.sin(.5*np.pi*np.clip((t-.54)/1.36, 0, 1)) ** 2
    mix[:len(t)] *= level[:, None]
    add(mix, motif, .13)
    add(mix, room(motif) * .19, .13)
    answer = fade(cut(motif, .0, .61), .03, .26)
    add(mix, answer * .43, 11 * BEAT + .10)
    add(mix, room(answer) * .12, 11 * BEAT + .10)

    # The mix rejoins the previous premaster exactly after the new vocal tail.
    assert np.isfinite(mix).all()
    assert np.array_equal(mix[sample(35):], previous[sample(35):])
    stem_path = HERE / f'{args.track}_placed_vocal.wav'
    sf.write(stem_path, new_lead, SR, subtype='FLOAT')
    path = HERE / f'{args.track}_mix.wav'
    sf.write(path, mix, SR, subtype='FLOAT')
    gain = -14.2 - float(loudness(path)['input_i'])
    target = HERE / f'{args.track}_mix.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-af',
                    f'volume={gain:.4f}dB,aresample=96000,alimiter=limit=0.82:attack=5:release=74:level=false:latency=true,aresample=44100',
                    '-metadata', 'title=What It Cost', '-metadata',
                    'artist=Kanye West × Travis Scott', '-c:a', 'libmp3lame',
                    '-b:a', '320k', str(target)], check=True)
    print('Vocal bounds', round(at, 3), round(stop, 3), 'Hook', round(HOOK_START, 3))
    print('Vocal/backing dB', round(20*np.log10(body(verse)/body(cut(backing, at, stop))), 2))
    print('Export', loudness(target))
    print(target)

if __name__ == '__main__':
    main()
