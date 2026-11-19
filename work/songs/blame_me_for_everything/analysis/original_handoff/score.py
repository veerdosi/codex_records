"""Write the two-bar Amaj9 to Bsus to E handoff."""
from pathlib import Path
import json
import pretty_midi as midi

here=Path(__file__).resolve().parent
beat=60/87

# A falling guitar answer plays against a picked bass figure in the
# first bar. On the second bar, E and F-sharp stay in the voicing
# as the bass moves to B and the top voice leads D-sharp back to E.
parts={
 'Guitar':[
    (.08,57,.76,58),(.11,64,.71,53),(.51,76,.51,73),
    (1.26,73,.62,65),(1.80,71,.46,61),(2.46,68,.56,63),
    (3.10,73,.48,62),(3.59,76,.62,67),
    (4.07,59,.66,60),(4.11,66,.83,50),(4.51,78,.57,69),
    (5.16,76,.64,63),(5.78,73,.46,56),(6.34,71,.57,61),
    (6.89,66,.46,53),(7.43,75,.43,60),(7.87,76,.94,56),
 ],
 'Keys':[
    (.24,52,3.54,51),(.30,56,3.32,48),(.38,61,3.19,52),
    (2.20,59,1.14,43),(4.04,54,3.58,52),(4.11,59,3.63,48),
    (4.22,64,3.34,49),(5.61,61,1.48,44),(7.25,63,.74,48),
    (7.93,64,.78,42),
 ],
 'Bass':[
    (.02,33,1.36,86),(1.73,33,.72,66),(2.64,40,.92,69),
    (3.65,33,.30,61),(4.01,35,1.42,85),(5.61,42,.52,67),
    (6.34,35,1.39,80),
 ],
 'Drums':[
    (0,36,.2,105),(1.73,36,.2,78),(2.60,36,.2,86),
    (1.01,37,.2,94),(3.01,37,.2,97),
    (4,36,.2,99),(5.62,36,.2,84),(6.33,36,.2,92),
    (5.01,37,.2,91),(7.01,37,.2,97),(7.64,37,.14,53),
    (.49,42,.1,53),(1.55,42,.1,44),(2.06,42,.1,61),
    (2.56,42,.1,49),(3.59,42,.1,54),(4.52,42,.1,57),
    (5.45,42,.1,47),(6.05,42,.1,63),(6.57,42,.1,54),
    (7.48,46,.19,48),
 ]
}
(here/'notes.json').write_text(json.dumps(parts,indent=2)+'\n')
for name,notes in parts.items():
    m=midi.PrettyMIDI(initial_tempo=87,resolution=960)
    instrument=midi.Instrument({'Guitar':24,'Keys':4,'Bass':38,'Drums':0}[name],
                              is_drum=name=='Drums',name=f'Veer | {name}')
    for t,p,d,v in notes:
        instrument.notes.append(midi.Note(v,p,t*beat,(t+d)*beat))
    m.instruments.append(instrument)
    m.write(str(here/f'{name}.mid'))
