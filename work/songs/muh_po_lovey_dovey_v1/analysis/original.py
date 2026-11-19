"""Original answering figures and FM texture, written against the Farebi bass pedal."""
from pathlib import Path
import os, sys, subprocess
import numpy as np
import pretty_midi as pm
import soundfile as sf
from pedalboard import Pedalboard, Reverb, HighpassFilter, LowpassFilter
from music21 import pitch

p=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(p.parents[1]/'shared/composition'))
from render_sfizz import render
lib=p.parents[1]/'shared/composition/instruments/FreePats'
media=Path(sys.argv[1])
media.mkdir(parents=True,exist_ok=True)
b=60/84
score=p/'analysis'
def midi(name,kind,events,sfz):
    m=pm.PrettyMIDI(initial_tempo=84)
    tr=pm.Instrument(pm.instrument_name_to_program(kind),name=name)
    for time,length,note,vel in events:
        tr.notes.append(pm.Note(vel,int(pitch.Pitch(note).midi),b*time,b*(time+length)))
    m.instruments.append(tr)
    f=score/(name+'.mid')
    m.write(str(f))
    path=media/(name+'.wav')
    render(f,sfz,path)
    x,sr=sf.read(path,dtype='float32')
    fx=Pedalboard([HighpassFilter(115 if 'Guitar' in name else 90),LowpassFilter(4800),
        Reverb(room_size=.30,damping=.71,wet_level=.19,dry_level=.86,width=.84)])
    y=fx(np.pad(x.T,((0,0),(0,int(sr*.75)))),sr).T
    sf.write(path,y*.43/(np.max(np.abs(y))+1e-10),sr,subtype='PCM_24')

# Fifths and octave doubles leave the mode open until the recorded hook enters.
piano=[]
intro=[
    (0,2.22,['E3','B3','G4','F#5'],[62,55,67,46]),
    (2.66,.68,['B3','E4','F#4'],[49,63,53]),
    (4.04,2.41,['E3','C4','G4','B4'],[58,65,60,49]),
    (6.51,.66,['C4','E4','F#4'],[47,49,60]),
    (7.42,.42,['B3','E4','G4'],[50,57,55]),
    (8.03,1.88,['E3','A3','C4','G4'],[58,55,60,64]),
    (10.52,.78,['A3','B3','E4','C5'],[45,53,58,56]),
    (12,2.08,['B2','A3','D#4','F#4'],[61,55,58,52]),
    (14.55,.36,['B3','C4','F#4'],[48,45,52]),
]
for q,length,chord,v in intro:
    piano += [(q+j*.024,max(.12,length-j*.05),n,v[j]) for j,n in enumerate(chord)]
for q,n in [(1.72,'B4'),(2.13,'G4'),(3.53,'E4'),(5.47,'F#5'),(5.96,'G5'),
            (7.7,'B4'),(9.52,'C5'),(10,'B4'),(11.26,'G4'),(13.26,'A4'),(13.89,'F#4')]:
    piano.append((q,.29,n,47))
# A quiet answer in the middle uses the same dominant-to-tonic motion.
for q, chord in [(152,['E3','B3','F#4']), (156,['B2','F#3','D#4'])]:
    piano += [(q+j*.019, 2.5+j*.26, n, [54,47,53][j]) for j,n in enumerate(chord)]
midi('Upright - frame','Acoustic Grand Piano',piano,next(lib.glob('Upright*/Upright*.sfz')))

motif=[(0,1.03,'B3',61),(.77,.72,'E4',67),(1.53,.56,'F#4',62),(2.51,1.11,'B4',62),
       (4.03,.8,'E4',58),(4.79,.65,'G4',63),(5.53,.6,'F#4',54),(6.69,1.13,'D#4',60)]
guitar=[(1.27,.49,'B3',59),(1.78,.68,'E4',66),(2.5,.77,'G4',57),
        (3.22,.46,'F#4',67),(3.78,.96,'B4',62),(5.20,.61,'E4',55),
        (5.74,.39,'G4',61),(6.02,.86,'B4',65),(6.74,.48,'F#4',55),
        (7.24,1.03,'E4',55),(8.49,.72,'C5',64),(9.23,.60,'B4',63),
        (9.77,1.28,'G4',63),(11.00,.41,'E4',57),(11.51,.45,'F#4',60),
        (12.04,.73,'A4',61),(12.76,.41,'F#4',59),(13.3,1.03,'D#4',60)]
for q,vel in [(152,-9),(260,-6),(268,-7)]:
    guitar += [(q+t,l,n,v+vel) for t,l,n,v in motif if t+q<278]
guitar += [(276.02,2.9,'E4',48),(276.07,2.78,'B3',43)]
midi('Nylon - answer','Acoustic Guitar (nylon)',guitar,next(lib.glob('Spanish*/Spanish*.sfz')))

# FM harmonics fade into the piano voicing and turn into the pickup before Calm.
csd='''<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=32
nchnls=2
0dbfs=1
instr 1
  iF = cpsmidinn(p4)
  aEnv linseg 0,p3*.23,1,p3*.43,.71,p3*.34,0
  kIdx linseg .42,p3*.63,1.07,p3*.37,.2
  aL foscil .075*aEnv,iF,1,2.002,kIdx,1
  aR foscil .075*aEnv,iF*.9989,1,2.004,kIdx,1
  aC oscili .075*aEnv,iF*.5,1
  outs aL+aC,aR+aC
endin
instr 2
  aEnv expon 1,p3,.001
  kIndex expon 4.7,p3,.12
  aHit foscil .047*aEnv,cpsmidinn(p4),1,2.77,kIndex,1
  aTilt tone aHit,2400
  outs aTilt,aTilt*.74
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
'''
for q,d,n in [(0,8,40),(8,4,40),(12,3.74,47),(150,6,40),(156,4,47),(256,8,40),(264,4,47),(268,10,40)]:
    csd+=f'i 1 {q*b:.7f} {d*b:.7f} {n}\n'
for q in [7.5,13.5,14.25,15,15.5,150.5,152,155.5,158,158.75,159.25,266.5,270.5]:
    csd+=f'i 2 {q*b:.7f} .4 76\n'
csd+='f 0 200\ne\n</CsScore>\n</CsoundSynthesizer>\n'
f=score/'FM.csd'
f.write_text(csd)
subprocess.run(['csound','-o',str(media/'FM - room.wav'),str(f)],check=True)
