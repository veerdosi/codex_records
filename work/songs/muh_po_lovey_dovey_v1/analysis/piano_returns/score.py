"""Voice the two turnaround cues and the answering stereo piano coda."""
from pathlib import Path
from fractions import Fraction
import json
import sys

import numpy as np
from pedalboard import HighpassFilter, LowpassFilter, Pedalboard, Reverb
import pretty_midi
import soundfile as sf
from scipy.signal import resample_poly

here=Path(__file__).resolve().parent
toolkit=here.parents[3]/'shared/composition'
piano=next((toolkit/'instruments').glob('FreePats/Upright*/*.sfz'))
sr=48000

def clock(stage):
    plan=json.loads((stage/'tempo.json').read_text())
    points=[0.]
    for (a,bpm,linear),(b,end,_) in zip(plan,plan[1:]):
        points.append(points[-1]+(b-a)*80/((bpm+end)/2 if linear else bpm))
    def at(t):
        i=np.clip(np.searchsorted([m[0] for m in plan],t,side='right')-1,0,len(plan)-2)
        a,bpm,linear=plan[i]
        slope=(plan[i+1][1]-bpm)/(points[i+1]-points[i]) if linear else 0
        return points[i] + 160*(t-a)/(bpm+np.sqrt(bpm*bpm+160*slope*(t-a)))
    return at

# Beat, duration, note, velocity, pan. The two cues share the same
# E–B pedal with a rising F-sharp, A, B answer.
cue=[
    (0,1.85,52,74,0),(0,1.55,59,74,-.30),(0,.9,66,69,.38),
    (.75,.84,69,66,-.46),(1.5,1.10,71,75,.51),
    (2.5,1.25,67,66,-.32),(3.25,1.4,66,63,.35),
]
coda=[
    (0,2.2,47,76,0),(0,2.,54,69,-.28),(.125,2.,62,73,-.38),
    (.5,1.3,69,71,.46),(1.25,1.3,66,71,-.48),(2,1.2,71,72,.51),
    (3,2.65,52,78,0),(3,2.40,59,73,-.26),(3.09,2.25,67,70,-.43),
    (3.30,2.05,66,65,.39),(3.62,1.85,71,68,.52),
    (4.35,1.15,76,63,-.36),
    (6.00,1.85,47,58,0),(6.00,1.7,66,60,-.43),
    (6.52,1.84,52,72,0),(6.63,1.70,59,66,-.30),
    (6.79,1.6,67,63,.45),(7.11,1.3,76,57,.33),
]
def print_piano(stage,label,events,position,at,length,level, *, treble=7600, echo=None):
    # Separate MIDI channels keep the piano voicings editable.
    printable=pretty_midi.PrettyMIDI(initial_tempo=85,resolution=960)
    instruments=[pretty_midi.Instrument(0,name=n) for n in ('Upright centre','Upright left','Upright right')]
    for (_,i),pan in zip(enumerate(instruments),(0,43,85)):
        i.control_changes.append(pretty_midi.ControlChange(10,64 if pan==0 else pan,0.))
    for t,d,n,v,p in events:
        i=0 if not p else 1 if p<0 else 2
        instruments[i].notes.append(pretty_midi.Note(v,n,at(position+t*.75)-at(position),at(position+(t+d)*.75)-at(position)))
    printable.instruments=instruments
    midi=stage/'Media'/f'Veer - {label}.mid'
    wav=stage/'Media'/f'Veer - {label}.wav'
    printable.write(str(midi))
    samples={
        pretty_midi.note_name_to_number(f.stem[:-2]):f
        for f in (piano.parent/'samples').glob('*vL.flac')
    }
    x=np.zeros((round(length*sr),2),dtype=np.float32)
    for when,duration,n,v,pan in events:
        start=round((at(position+when*.75)-at(position))*sr)
        samples_long=round((at(position+(when+duration)*.75)-at(position+when*.75)+.36)*sr)
        root=min(samples,key=lambda k:abs(n-k))
        y,rate=sf.read(samples[root],dtype='float32',always_2d=True)
        factor=Fraction(sr/rate * 2**((root-n)/12)).limit_denominator(512)
        y=resample_poly(y,factor.numerator,factor.denominator,axis=0)
        y=y[:min(samples_long,len(x)-start)]
        y=y.mean(axis=1)
        attack=round(sr*.003)
        y[:attack]*=np.linspace(0,1,attack)
        tail=min(len(y),round(sr*.36))
        y[-tail:]*=np.linspace(1,0,tail)**1.45
        gain=(v/82)**1.65*np.sqrt([1-pan,1+pan])
        x[start:start+len(y)]+=y[:,None]*gain
    dry=Pedalboard([HighpassFilter(91),LowpassFilter(treble)])(x.T,sr).T
    # Keep the whole direct signal in stereo. Crossed echoes sit
    # underneath at a lower level and have no polarity inversion.
    wet=Pedalboard([HighpassFilter(420),LowpassFilter(3100),
           Reverb(room_size=.31,damping=.70,wet_level=.30,dry_level=.7,width=.88)])(dry.T,sr).T
    step=round(sr*(at(position+.5625)-at(position)))
    if echo is None:
        echo = (.24,.13,.052) if label=='Upright coda' else (.15,.068)
    for cnt,g in enumerate(echo,1):
        delay=step*cnt
        dry[delay:]+=g*wet[:-delay,::-1]
    dry=.82*dry+.18*wet
    size=round(length*sr)
    dry=np.pad(dry[:size],((0,max(0,size-len(dry))),(0,0)))
    fade=round(sr*.24)
    dry[-fade:]*=np.linspace(1,0,fade)[:,None]
    win=max(np.sqrt(np.mean(s*s)) for s in np.array_split(dry, max(1,round(len(dry)/sr/.25))))
    dry*=10**(level/20)/max(win,1e-8)
    sf.write(wav,dry,sr,'PCM_24')
    return [wav.name,at(position),len(dry)/sr]

if __name__ == '__main__':
    for variant in ('native','fixed'):
        stage=here/variant
        at=clock(stage)
        encore,calm,coda_at=(93.75,180.777375,220.5) if variant=='native' else (93.75,177.375,214.5)
        end=229.5 if variant=='native' else 223.5
        configs=[
            ('Encore piano cue',cue,encore,3.87,-25),
            ('Calm piano cue',cue,calm,3.87,-25),
            ('Upright coda',coda,coda_at,at(end)-at(coda_at),-24),
        ]
        data=[print_piano(stage,*c[:3],at,*c[3:]) for c in configs]
        (stage/'piano.json').write_text(json.dumps(data))
