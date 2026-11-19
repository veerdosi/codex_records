"""Write the eight-bar original upright piano outro."""
from pathlib import Path
import pretty_midi as pm

here = Path(__file__).resolve().parent
midi = pm.PrettyMIDI(initial_tempo=87,resolution=960)
piano = pm.Instrument(0,name='Veer | Upright piano')
beat = 60/87

# The right hand takes up the contour of the turnaround, then resolves
# from F-sharp minor and a suspended dominant to the final E add9.
left = [
    (40,47,56,63), (37,44,52,59), (33,45,52,56), (35,47,54,64),
    (42,49,52,56), (33,45,52,59), (35,47,54,63), (40,47,54,56),
]
right = [
    [(0.48,71,.85,66),(1.59,68,.65,59),(2.43,66,.74,57),(3.29,64,.91,62)],
    [(0.16,64,1.5,59),(1.93,68,.61,55),(2.73,71,.80,62),(3.48,73,.67,56)],
    [(0.14,71,.94,63),(1.35,69,.66,59),(2.24,68,1.06,55),(3.48,64,.69,54)],
    [(0.28,66,1.32,60),(1.87,64,.81,52),(2.89,63,1.23,54)],
    [(0.13,68,.98,63),(1.37,69,.58,59),(2.13,73,1.34,63),(3.48,71,.60,56)],
    [(0.32,68,1.04,59),(1.76,66,.61,57),(2.62,64,1.36,54)],
    [(0.26,66,.96,60),(1.48,64,.67,55),(2.48,63,1.30,53)],
    [(0.12,64,2.94,64),(0.31,71,2.37,51),(2.25,66,1.56,46)],
]
for measure,(harmony,melody) in enumerate(zip(left,right)):
    base = 4*measure
    for i,note in enumerate(harmony):
        time = (base+[.018,.09,.48,1.38][i])*beat
        end = (base+(3.82 if measure<7 else 4.05))*beat
        velocity = [60,51,48,43][i]+[0,-3,-2,0,1,-3,-4,-2][measure]
        piano.notes.append(pm.Note(velocity,note,time,end))
    for at,note,duration,velocity in melody:
        piano.notes.append(pm.Note(velocity,note,(base+at)*beat,(base+at+duration)*beat))
    piano.control_changes.append(pm.ControlChange(64,67,(base+.20)*beat))
    piano.control_changes.append(pm.ControlChange(64,0,(base+3.94)*beat))
midi.instruments.append(piano)
midi.write(str(here/'Veer piano outro.mid'))
