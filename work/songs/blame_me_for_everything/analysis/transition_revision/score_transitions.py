"""Write the piano, cello and bass phrases connecting the existing sections."""
from pathlib import Path
import json
import pretty_midi as pm

here=Path(__file__).resolve().parent
beat=60/87
bar=4*beat
parts={'Upright':[],'Cello':[],'Bass':[]}

def phrase(name,measure,notes):
    for offset,pitch,length,velocity in notes:
        t=(measure*4+offset)*beat
        parts[name].append((t,pitch,length*beat,velocity))

# The low and high piano share E before the bass makes A-to-E audible.
phrase('Upright',1,[(2.45,52,1.70,53),(3.32,59,1.26,48)])
phrase('Upright',2,[(.37,64,1.08,50),(1.58,66,.53,45),(2.28,64,1.28,50)])
phrase('Cello',1,[(3.03,52,4.92,46),(3.66,56,3.72,35)])
phrase('Upright',5,[(1.71,61,.80,55),(2.72,64,1.60,60),(3.34,66,.64,52)])
phrase('Upright',6,[(.10,64,1.20,54),(.26,59,1.66,48)])
phrase('Cello',5,[(2.21,52,4.05,48),(3.10,47,2.63,42)])

# The original first hook has a dominant-to-tonic lift already.
phrase('Cello',13,[(2.73,54,2.75,40),(3.35,59,2.35,43)])
phrase('Upright',13,[(3.42,63,.58,48)])
phrase('Upright',14,[(.08,64,1.06,47)])

# B and D-sharp bring the hook home to E. Repeat B a register up as
# the verse changes the harmony underneath it.
phrase('Bass',21,[(1.86,35,1.66,69),(3.48,39,.49,62)])
phrase('Upright',21,[(2.66,66,.63,62),(3.48,63,.60,58)])
phrase('Upright',22,[(.07,64,1.25,66),(.19,59,1.76,52),(2.09,68,.66,56)])
phrase('Upright',23,[(.32,71,1.09,65),(1.76,68,.53,55),(2.55,66,.75,52),(3.44,71,.87,53)])
phrase('Cello',22,[(.30,52,3.46,52),(.53,56,3.50,43)])
phrase('Cello',23,[(1.13,59,3.98,51),(2.08,54,2.94,41)])
phrase('Upright',24,[(2.54,71,.66,48)])

# After Savage's line the shared E and F-sharp carry Amaj7 through
# Bsus4. The D-sharp at the end resolves just before Kanye's pickup.
phrase('Upright',34,[(3.42,73,.78,59)])
phrase('Upright',35,[(.14,76,.91,65),(1.30,71,.62,56),(2.06,66,1.41,59),
                     (3.57,63,.56,56)])
phrase('Upright',36,[(.22,64,1.66,60),(.38,59,1.26,47)])
phrase('Cello',34,[(3.45,52,4.99,57),(3.90,57,1.76,42)])
phrase('Cello',35,[(1.91,54,3.37,53),(3.45,47,1.48,42)])
phrase('Bass',35,[(2.05,35,1.80,77)])

# The four-bar lift grows from one piano line into moving cello voices.
phrase('Upright',44,[(.27,71,.83,63),(1.30,68,.73,59),(2.26,66,1.19,57),(3.58,64,.59,62)])
phrase('Cello',44,[(.19,52,3.38,47),(1.50,47,2.49,50)])
phrase('Upright',45,[(.16,68,.72,63),(1.26,71,.93,65),(2.58,75,1.11,66)])
phrase('Cello',45,[(.11,56,2.63,54),(2.43,59,1.58,53)])
phrase('Upright',46,[(.17,76,1.02,68),(1.45,73,.75,62),(2.46,71,.79,58),(3.48,68,.65,56)])
phrase('Cello',46,[(.20,57,2.65,56),(1.81,64,2.30,51),(2.86,61,1.18,54)])
phrase('Upright',47,[(.22,69,.87,60),(1.20,73,.78,63),(2.37,76,1.50,66),
                     (3.51,78,.67,61)])
phrase('Cello',47,[(.12,54,1.86,57),(1.88,57,1.52,56),(2.81,64,3.88,54)])
phrase('Upright',48,[(.20,76,1.70,58),(1.26,71,1.31,52)])
phrase('Cello',48,[(.24,56,2.82,46)])

# Reprise cadence and the first notes of the actual outro melody,
# played on the same upright so the final hook is already thinning into it.
phrase('Cello',55,[(2.50,54,2.29,44),(3.55,59,1.42,44)])
phrase('Upright',63,[(.64,71,.66,57),(1.82,68,.73,54),(3.43,66,.64,51)])
phrase('Cello',63,[(1.78,56,3.29,49),(2.21,52,3.78,45)])

for name,program in [('Upright',0),('Cello',42),('Bass',38)]:
    midi=pm.PrettyMIDI(initial_tempo=87,resolution=960)
    inst=pm.Instrument(program,name=f'Veer | {name}')
    for t,p,d,v in sorted(parts[name]):
        inst.notes.append(pm.Note(v,p,t,t+d))
    midi.instruments.append(inst)
    midi.write(str(here/f'{name} transitions.mid'))
(here/'notes.json').write_text(json.dumps(parts,indent=2)+'\n')
