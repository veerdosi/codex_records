"""Rephrase the synth after bar one and leave Farebi's pre-chorus fill open."""
from pathlib import Path
import subprocess
import sys

import numpy as np
from pedalboard import HighpassFilter, Pedalboard, Reverb
import soundfile as sf

folder = Path(__file__).resolve().parent
media = Path(sys.argv[1])
# Reuse the opening's notes and sound. Ease the figure down in register
# before the source bass and lead take over at 9s.
plucks = [
    (3.0035, .36, 59, .044, .40), (3.0035, .32, 66, .036, .58),
    (3.7534, .21, 71, .043, .47), (4.1482, .19, 66, .041, .54),
    (4.50, .61, 64, .045, .44), (4.50, .57, 71, .034, .58),
    (5.25, .22, 66, .039, .47), (5.625, .23, 71, .041, .53),
    (6.0035, .38, 64, .043, .44), (6.0035, .33, 71, .039, .60),
    (6.7561, .22, 76, .054, .52), (7.1287, .23, 78, .048, .52),
    (7.8781, .25, 76, .051, .48), (8.2536, .21, 71, .043, .51),
    (8.6076, .20, 64, .036, .47), (8.6076, .20, 71, .027, .58),
]
pulses = [
    (3.0035, .29, 47, .068, .49), (4.50, .52, 52, .081, .49),
    (5.25, .24, 47, .062, .49), (6.0035, .36, 52, .088, .49),
    (7.8781, .24, 52, .065, .49),
]
ticks = [
    (4.689, .063, 5800, .026, .63), (5.4375, .063, 6700, .031, .63),
    (5.8125, .060, 7400, .025, .63), (8.434, .061, 6700, .031, .63),
]
for layer, phrase in enumerate([plucks, pulses, ticks], 1):
    source = folder.parent / 'harmony' / f'Layer {layer}.csd'
    orchestra, score = source.read_text().split('<CsScore>\n', 1)
    retained = [
        line for line in score.splitlines()
        if line.startswith('i ') and float(line.split()[2]) < 3
    ]
    retained += [
        f'i {layer} {t:.6f} {dur:.6f} {pitch} {gain:.6f} {pan:.4f}'
        for t, dur, pitch, gain, pan in phrase
    ]
    csd = folder / f'Intro layer {layer}.csd'
    csd.write_text(orchestra + '<CsScore>\nf 1 0 4096 10 1\n'
                   + '\n'.join(retained) + '\nf 0 9.03\ne\n</CsScore>\n</CsoundSynthesizer>\n')
    wave = media / f'Veer - intro pickup {layer}.wav'
    subprocess.run(['csound', '-o', str(wave), str(csd)], check=True)
    audio, rate = sf.read(wave, dtype='float32')
    board = Pedalboard([
        HighpassFilter(140 if layer == 1 else 55),
        Reverb(room_size=.28, damping=.69, wet_level=.13, dry_level=.91, width=.89),
    ])
    audio = board(audio.T, rate).T
    original, original_rate = sf.read(media / f'Veer - harmony {layer}.wav', dtype='float32')
    assert rate == original_rate == 48000
    boundary = 3 * rate
    overlap = 96
    audio[:boundary] = original[:boundary]
    blend = np.linspace(0, 1, overlap, endpoint=False)[:, None]
    audio[boundary:boundary + overlap] = (
        original[boundary:boundary + overlap] * (1 - blend)
        + audio[boundary:boundary + overlap] * blend
    )
    fade_start = round(8.835 * rate)
    fade_end = 9 * rate
    audio[fade_start:fade_end] *= np.linspace(1, 0, fade_end - fade_start)[:, None]
    sf.write(wave, audio[:fade_end], rate, subtype='PCM_24')
