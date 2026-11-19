"""Write a single answer over the E pedal before Savage's verse."""
from pathlib import Path
import pretty_midi as midi

here=Path(__file__).resolve().parent
beat=60/87
score=midi.PrettyMIDI(initial_tempo=87,resolution=960)
piano=midi.Instrument(0,name='Veer | Upright piano answer')
# E–G-sharp–B is stated once, then shortened to E–B. The B
# belongs to the incoming harmony, and the last note decays
# before the vocal pickup.
for at,pitch,duration,velocity in [(1.0,64,.82,60),(1.74,68,.56,54),
                                   (2.48,71,.92,57),(4.73,64,.68,56),
                                   (5.49,71,1.24,61)]:
    piano.notes.append(midi.Note(velocity,pitch,at*beat,(at+duration)*beat))
score.instruments.append(piano)
score.write(str(here/'Upright answer.mid'))
