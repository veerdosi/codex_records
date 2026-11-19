"""Write two variations on Runaway's high piano pulse."""
import json
from pathlib import Path
import pretty_midi as pm

here=Path(__file__).resolve().parent
beat=60/87

# The original high E moves from a bare pulse to a call and response.
# The lower phrase descends B, G-sharp, F-sharp, E across both bookends.
intro = [
    ((),[(1.31,71,.81,55),(3.27,68,.75,57)]),
    ((40,47,54,56),[(1.13,71,.83,58),(2.88,68,.50,54),(3.49,66,.60,49)]),
    ((37,44,52,59),[(.71,64,1.54,59),(2.71,71,.89,55),(3.62,68,.49,49)]),
    ((37,44,52,59),[(1.30,68,.91,54),(2.75,66,.45,49),(3.28,64,.74,56)]),
    ((33,45,52,56),[(.73,73,1.13,56),(2.85,71,.68,57),(3.56,68,.57,53)]),
    ((33,45,52,61),[(.77,66,.82,58),(1.75,64,1.12,56),(3.07,59,1.64,53)]),
]
outro = [
    ((),[(2.63,71,.59,49),(3.31,68,.81,45)]),
    ((40,47,54,56),[(1.25,71,.87,59),(2.91,68,.53,56),(3.53,66,.58,50)]),
    ((40,47,51,56),[(.67,64,1.21,59),(2.71,68,.65,53),(3.42,71,.65,58)]),
    ((37,44,52,59),[(.76,76,1.28,59),(2.66,71,.65,55),(3.33,68,.75,54)]),
    ((37,44,52,59),[(.83,68,1.15,54),(2.84,66,.49,52),(3.32,64,.64,55)]),
    ((33,45,52,56),[(.77,73,1.10,58),(2.50,71,.87,54),(3.41,68,.72,51)]),
    ((33,45,52,61),[(.74,66,.75,55),(1.58,64,1.56,56),(3.37,71,.67,53)]),
    ((35,47,52,54),[(.42,69,.86,51),(1.73,66,.91,52),(3.21,63,.88,54)]),
    ((40,47,54,56),[(.56,64,3.46,60),(1.62,71,1.86,48),(2.44,66,1.38,45)]),
]

def write(name,bars):
    midi=pm.PrettyMIDI(initial_tempo=87,resolution=960)
    inst=pm.Instrument(0,name=f'Veer | {name} piano')
    def note(time,pitch,duration,velocity):
        inst.notes.append(pm.Note(velocity,pitch,time*beat,(time+duration)*beat))
    for i,(chord,melody) in enumerate(bars):
        base=4*i
        if chord:
            for offset,pitch,velocity in zip([.01,.12,.36,1.10],chord,[59,52,49,47]):
                note(base+offset,pitch,(4.27 if i==len(bars)-1 else 3.65)-offset,velocity)
        for time,pitch,duration,velocity in melody:
            note(base+time,pitch,duration,velocity)
        inst.control_changes.append(pm.ControlChange(64,74,(base+.21)*beat))
        inst.control_changes.append(pm.ControlChange(64,0,(base+3.94)*beat))
    midi.instruments.append(inst)
    midi.write(str(here/f'{name}.mid'))

write('Opening upright',intro)
write('Closing upright',outro)
motif={
    'opening':[
        (0,0,88,78),(0,2,88,68),(1,0,88,70),(1,2,88,64),
        (2,0,88,66),(2,2,88,60),(3,0,80,57),(3,2,88,62),
        (4,0,88,65),(4,2,85,61),(5,0,83,60),(5,2,88,57)
    ],
    'closing':[
        (63,2,88,40),(64,0,88,61),(64,2,88,59),(65,0,88,62),
        (65,2,88,55),(66,0,88,59),(66,2,85,55),(67,0,80,52),
        (67,2,88,54),(68,0,88,58),(68,2,85,54),(69,0,83,52),
        (69,2,88,49),(70,0,83,51),(70,2,80,46),(71,0,76,52)
    ]
}
(here/'motif.json').write_text(json.dumps(motif,indent=2)+'\n')
