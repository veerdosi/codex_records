"""Score a pickup and two bars using the measured Runaway accents."""
from pathlib import Path
import json
import pretty_midi as midi

here=Path(__file__).resolve().parent
beat=60/87
# Negative offsets are the last beat of Savage's verse. E and B are
# common to its C-sharp minor harmony and the first Amaj9 voicing.
parts={
 'Pickup guitar':[(-.84,76,.81,59),(-.37,71,.92,51)],
 'Pickup keys':[(-.99,64,1.36,47),(-.53,59,1.22,44)],
 'Bass':[(.012,33,2.28,86),(2.50,33,.79,76),(3.45,40,.49,62),
         (4.015,35,.41,89),(4.50,35,1.69,77),(6.49,35,1.19,82)],
 'Drums':[
    (0,36,.18,102),(2.48,36,.18,88),
    (4,36,.18,99),(4.49,36,.17,77),(6.48,36,.17,91),
    (.98,37,.16,94),(2.98,37,.16,100),
    (4.98,37,.16,93),(6.98,37,.16,98),(7.66,37,.12,55),
    (-.17,42,.09,41),(.014,42,.09,48),(.47,42,.09,53),(.98,42,.09,41),
    (1.49,42,.09,56),(1.98,42,.09,44),(2.47,42,.09,46),
    (2.98,42,.09,59),(3.49,42,.09,49),
    (4.47,42,.09,54),(4.98,42,.09,46),(5.24,42,.09,41),
    (5.49,42,.09,61),(5.98,42,.09,46),(6.98,42,.09,60),
    (7.48,46,.18,48),
 ]
}
(here/'notes.json').write_text(json.dumps(parts,indent=2)+'\n')
for name,notes in parts.items():
    m=midi.PrettyMIDI(initial_tempo=87,resolution=960)
    part=midi.Instrument({'Pickup guitar':24,'Pickup keys':4,'Bass':38,'Drums':0}[name],
                         is_drum=name=='Drums',name=f'Veer | {name}')
    for at,pitch,duration,velocity in notes:
        start=(1+at)*beat
        part.notes.append(midi.Note(velocity,pitch,start,start+duration*beat))
    m.instruments.append(part)
    m.write(str(here/f'{name}.mid'))
