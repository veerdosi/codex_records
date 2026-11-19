"""Play shorter responses in the openings of the Farebi backing."""
from pathlib import Path
import json
import sys

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'piano_returns'))
from score import clock, print_piano

for variant in ('fixed','native'):
    stage=here/variant
    native=variant=='native'
    at=clock(stage)
    # The accented hits follow the same subdivision as the percussion.
    # The opening is an E/B pair. Change the response with the backing.
    encore=[
        (.13,.15,64,70,-.02),(.13,.13,71,62,.02),
        (.49,.105,67,59,0),(.81,.105,71,65,0),
        (1.08,.11,76,62,0),(1.32,.10,71,58,0),
        (2.42,.105,72 if native else 71,59,0),
        (2.76,.14,76 if native else 75,57,0),
    ]
    calm=[
        (.10,.15,64,70,-.02),(.10,.13,71,62,.02),
        (.49,.105,67,59,0),(.81,.105,71,65,0),
        (1.08,.11,76,62,0),(1.32,.10,71,58,0),
        (2.48,.10,71,60,0),(2.74,.12,75,58,0),
    ]
    if native:
        calm[-1]=(2.78,.12,76,58,0)
    # The original B7–Bm7 motion stays present as the piano answers.
    # Retain the slower sustained E voicing only after the final beat.
    coda=[
        (.27,.30,66,67,-.32),(.51,.22,75,60,.31),(.81,.29,69,65,-.23),
        (1.76,.34,62,65,-.38),(2.02,.28,66,67,.42),
        (2.53,.30,69,63,-.44),(2.77,.29,71,65,.35),
        (3.27,.21,66,61,-.34),(3.76,.35,71,66,.42),
        (4.58,1.12,52,73,0),(4.63,1.0,59,67,-.25),
        (4.74,1.1,67,67,.45),(4.90,.74,71,63,-.40),
        (5.13,.81,76,60,.38),(7.17,1.60,64,57,-.36),
        (7.28,1.47,71,55,.34),
    ]
    anchor=(93.75,180.777375,220.5) if native else (93.75,177.375,214.5)
    ends=229.5 if native else 223.5
    clips=[]
    for label,events,pos,length,level,treble,echo in [
        ('Encore piano pulse',encore,anchor[0],3.48,-27.1,5700,(.038,)),
        ('Calm piano pulse',calm,anchor[1],3.48,-27.1,5700,(.038,)),
        ('Upright and echo ending',coda,anchor[2],at(ends)-at(anchor[2]),-25.6,6600,(.19,.086,.035)),
    ]:
        # The score clocks both the audio and editable MIDI to the ramp.
        clips.append(print_piano(stage,label,events,pos,at,length,level,treble=treble,echo=echo))
    (stage/'piano.json').write_text(json.dumps(clips))
