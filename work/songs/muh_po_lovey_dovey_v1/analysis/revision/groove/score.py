"""Score the synth replies against the measured Farebi drum transients."""
from pathlib import Path
import json
import subprocess
import sys
import numpy as np
from pedalboard import HighpassFilter, Pedalboard, Reverb
import soundfile as sf

analysis = Path(__file__).resolve().parent
media = Path(sys.argv[1])
score = {1: [], 2: [], 3: []}

# Downstrokes coincide with measured drum attacks. A few single-note replies
# use the intervening sixteenths. The first cell returns after the drum break.
main = [
    (.0131, (64, 71), .20, .077), (.3784, (71,), .14, .055),
    (.7565, (66, 76), .19, .068), (1.1289, (71,), .13, .050),
    (1.8816, (64, 71), .17, .068), (2.2651, (66, 76), .19, .069),
    (2.6288, (71,), .14, .056),
    (3.0035, (63, 69, 71), .21, .072), (3.3781, (66,), .14, .054),
    (3.7534, (69, 71), .17, .064), (4.1482, (66,), .15, .055),
    (4.500, (71,), .22, .054), (4.875, (69,), .19, .046),
    (5.250, (66,), .22, .049), (5.625, (63,), .19, .040),
    (6.0035, (64, 71), .20, .079), (6.3806, (71,), .14, .058),
    (6.7561, (66, 76), .19, .071), (7.1287, (71,), .13, .052),
    (7.8781, (64, 71), .18, .064), (8.2536, (66, 76), .19, .069),
    (8.6076, (71,), .14, .052),
    (9.0033, (66, 69), .17, .058), (9.3778, (73,), .14, .048),
    (9.7482, (66, 69), .15, .043),
]
answers = [
    (.938, 83, .15), (2.445, 78, .13), (2.821, 76, .12),
    (3.938, 81, .13), (5.8125, 78, .12),
    (6.938, 83, .14), (8.434, 78, .13), (8.817, 76, .11),
    (9.936, 78, .10),
]
# The two shorter replies follow their own backing harmony.
turnaround = [
    (.039, (64, 71), .21, .065), (.388, (67,), .13, .047),
    (.787, (64, 71), .16, .054), (1.16, (71,), .13, .049),
    (1.528, (66, 69), .18, .057), (1.914, (73,), .14, .047),
    (2.276, (66, 69), .18, .050), (2.66, (78,), .12, .037),
]
coda = [
    (.030, (67, 71), .24, .064), (.378, (71,), .14, .051),
    (.776, (67, 74), .20, .056), (1.128, (71,), .15, .043),
    (1.546, (66, 69), .22, .053), (1.878, (66,), .14, .042),
    (2.276, (69, 73), .18, .041), (2.654, (66,), .30, .035),
    (3.375, (66,), .21, .029),
]


def add_stabs(start, notes):
    for time, pitches, duration, volume in notes:
        for voice, pitch in enumerate(pitches):
            pan = (.44, .63, .26)[voice]
            score[1].append((start + time, duration, pitch, volume / len(pitches)**.66, pan))


add_stabs(0, main)
add_stabs(12, turnaround)
add_stabs(15, coda)
for i, (time, pitch, duration) in enumerate(answers):
    score[1].append((time, duration, pitch, .023, .24 if i % 2 else .76))

# Short, filtered notes support the riff in the gaps. Cut the pulse before the
# C# bass and the sung pickup arrive. Metal hits mark only the phrase endings.
for time, pitch, duration, volume in [
    (.013, 52, .30, .105), (.757, 52, .23, .080),
    (1.882, 52, .26, .096), (2.265, 59, .21, .077),
    (3.003, 47, .27, .099), (3.753, 47, .28, .085),
    (4.500, 47, .42, .090), (5.250, 47, .38, .083),
    (6.003, 52, .30, .107), (6.756, 52, .24, .088),
    (7.878, 52, .24, .095), (8.254, 59, .24, .081),
    (15.030, 55, .22, .060), (16.546, 54, .30, .058),
]:
    score[2].append((time, duration, pitch, volume, .49))
for time, cutoff, gain in [
    (1.685, 5400, .039), (2.444, 7200, .052), (2.821, 7900, .034),
    (4.689, 5800, .038), (5.4375, 6700, .045), (5.8125, 7800, .030),
    (7.693, 5400, .040), (8.434, 6800, .046), (8.818, 7800, .038),
    (9.941, 7100, .028), (12.972, 5500, .035), (14.09, 7000, .037),
    (14.846, 7800, .026), (16.329, 6300, .028), (17.468, 7500, .025),
]:
    score[3].append((time, .063, cutoff, gain, .63))

orchestra = '''<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=32
nchnls=2
0dbfs=1
instr 1
  iFreq = cpsmidinn(p4)
  aEnv linseg 0,.0035,1,.026,.64,p3-.0295,0
  kIndex expon 1.82,p3,.19
  aCore foscil p5*aEnv,iFreq,1,2,kIndex,1
  aWidth foscil p5*aEnv*.21,iFreq*1.003,1,2.002,kIndex,1
  aTone tone aCore+aWidth,5200
  outs aTone*sqrt(1-p6),aTone*sqrt(p6)
endin
instr 2
  iFreq = cpsmidinn(p4)
  aEnv linseg 0,.006,1,.045,.52,p3-.051,0
  kCut expon 1120,p3,320
  aRaw vco2 p5,iFreq,12
  aPulse moogladder aRaw,kCut,.17
  outs aPulse*aEnv*.73,aPulse*aEnv*.69
endin
instr 3
  aEnv expon 1,p3,.001
  aNoise noise p5*aEnv,0
  aMetal butterbp aNoise,p4,p4*.65
  aRing oscili p5*aEnv*.14,p4*.57,1
  outs (aMetal+aRing)*sqrt(1-p6),(aMetal+aRing)*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
'''
for instrument, events in score.items():
    score_text = ''.join(
        f'i {instrument} {t:.6f} {d:.6f} {pitch} {gain:.6f} {pan:.4f}\n'
        for t, d, pitch, gain, pan in sorted(events)
    )
    csd = analysis / f'Layer {instrument}.csd'
    csd.write_text(orchestra + score_text + 'f 0 18.8\ne\n</CsScore>\n</CsoundSynthesizer>\n')
    wave = media / f'Veer - pocket {instrument}.wav'
    subprocess.run(['csound', '-o', str(wave), str(csd)], check=True)
    x, sample_rate = sf.read(wave, dtype='float32')
    board = Pedalboard([
        HighpassFilter(140 if instrument == 1 else 55),
        Reverb(room_size=.20, damping=.70, wet_level=.085, dry_level=.94, width=.89),
    ])
    sf.write(wave, board(x.T, sample_rate).T, sample_rate, subtype='PCM_24')
(analysis / 'drum_anchors.json').write_text(
    json.dumps([row[0] for row in main if not 4.4 < row[0] < 5.9], indent=2) + '\n'
)
