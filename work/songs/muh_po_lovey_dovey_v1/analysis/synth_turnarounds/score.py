"""Compose dry synth replies and a stereo echo using a new subtractive patch."""
from pathlib import Path
from subprocess import run
import json

import pretty_midi

stage = Path(__file__).resolve().parent
orchestra = '''<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=16
nchnls=2
0dbfs=1
instr 1
  iFreq = cpsmidinn(p4)
  aAmp linseg 0,.0036,1,.029,.65,p3-.0326,0
  kCut expon 4200,p3,620
  aPulse vco2 .51,iFreq,2,.28
  aOctave vco2 .18,iFreq*2,12
  aBody moogladder aPulse+aOctave,kCut,.16
  aBloom oscili .19,iFreq,1
  aSignal atone (aBody+aBloom)*aAmp*p5*2.15,180
  outs aSignal*sqrt(1-p6),aSignal*sqrt(p6)
endin
</CsInstruments>
'''
beat = 60 / 85

# Within each turnaround, the E–B figure alternates between the
# measured kick / snare hits. The short upper answer follows the
# local chord change and leaves the Farebi vocal pickup clear.
parts = [
    ('Encore synth reply', 88.170352941176, 3.15, [
        (.066, .16, 64, .095, .5), (.073, .125, 71, .043, .5),
        (.397, .12, 67, .058, .5), (.773, .15, 71, .083, .5),
        (1.104, .12, 76, .069, .5), (1.285, .082, 71, .044, .5),
        (1.645, .13, 76, .063, .34), (1.814, .14, 71, .048, .66),
        (2.186, .15, 75, .071, .45), (2.350, .12, 78, .045, .6),
        (2.707, .18, 71, .054, .5),
    ]),
    ('Calm synth reply', 166.898823529412, 3.15, [
        (.032, .15, 64, .100, .5), (.040, .12, 71, .039, .5),
        (.388, .12, 67, .063, .5), (.732, .15, 71, .086, .5),
        (1.007, .116, 76, .072, .5), (1.181, .082, 71, .049, .5),
        (1.439, .12, 75, .063, .34), (1.797, .13, 71, .049, .65),
        (2.142, .16, 75, .068, .46), (2.502, .15, 80, .052, .64),
        (2.681, .19, 75, .054, .50),
    ]),
]

# Echo the last synth answer into the coda. The source changes from
# B7 to Bm7, so the upper third descends before the final E voicing.
outro = []
for when, length, note, amplitude, pan in [
    (1.50,.31,71,.043,.43), (1.75,.24,75,.047,.56),
    (2.25,.24,78,.045,.40), (2.75,.25,74,.051,.62),
    (3.25,.22,69,.049,.29), (3.75,.36,71,.071,.55),
    (4.50,.22,66,.043,.38), (4.75,.28,74,.048,.62),
    (5.50,.40,71,.064,.45), (6.25,.48,64,.077,.50),
    (6.27,.47,71,.054,.41), (6.38,.40,67,.042,.60),
    (6.77,.40,76,.057,.50),
]:
    outro.append((when*beat,length,note,amplitude,pan))
    if when>3.5:
        for tap,gain in enumerate((.29,.15,.068),1):
            outro.append(((when+tap*.75)*beat,length,note,amplitude*gain,
                          .85 if tap%2 else .15))
parts.append(('Synth echo ending',200.470588235294,6.9,outro))

# V2's pickup runs from just after the word edge to just before the
# speed-up. The same two pitches cue both ramps at the verse tempo.
pre_ramp = [
    (.013,.105,64,.140,.31),(.022,.09,71,.072,.41),
    (.173,.144,76,.124,.67),(.181,.111,71,.069,.58),
]
short = 60/82/2
v2parts = [
    ('Encore pre-ramp synth',89.193932437720-short,short-.026,pre_ramp),
    ('Calm pre-ramp synth',171.802540106952-short,short-.026,pre_ramp),
    ('Ramp mix synth echo ending',206.742894385027,6.9*85/88,
        [(when*85/88,length,note,gain,pan) for when,length,note,gain,pan in outro]),
]

clips = []
for label, position, duration, notes in parts+v2parts:
    name=f'Veer - {label}'
    csd=stage/'Media'/f'{name}.csd'
    wav=csd.with_suffix('.wav')
    text=''.join(f'i 1 {t:.6f} {l:.6f} {n} {g:.6f} {p:.6f}\n' for t,l,n,g,p in sorted(notes))
    csd.write_text(orchestra+'<CsScore>\nf 1 0 4096 10 1\n'+text+f'f 0 {duration}\ne\n</CsScore>\n')
    run(['csound','-o',str(wav),str(csd)],check=True)
    score=pretty_midi.PrettyMIDI(initial_tempo=85,resolution=960)
    voice=pretty_midi.Instrument(81,name='Veer FM pluck')
    voice.notes=[pretty_midi.Note(round(min(g*770+21,127)),n,t,t+l)
                 for t,l,n,g,_ in notes if g>.031]
    score.instruments.append(voice)
    score.write(str(csd.with_suffix('.mid')))
    clips.append([name+'.wav',position,duration])
(stage/'clips.json').write_text(json.dumps(clips))
