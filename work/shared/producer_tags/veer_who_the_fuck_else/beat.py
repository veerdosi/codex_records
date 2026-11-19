"""Write the original one-bar score for the producer tag."""
from pathlib import Path
import pretty_midi as midi

analysis = Path(__file__).resolve().parent / 'analysis'
tempo = 96

def write(name, instrument, events):
    song = midi.PrettyMIDI(initial_tempo=tempo, resolution=960)
    for pitch, start, length, velocity in events:
        instrument.notes.append(midi.Note(velocity, pitch, start, start+length))
    song.instruments.append(instrument)
    song.write(str(analysis / f'{name}.mid'))

write('upright', midi.Instrument(0, name='Upright piano'), [
    (53,.019,.48,77), (56,.029,.43,72), (60,.042,.41,68), (67,.053,.31,54),
    (63,.640,.33,70), (60,.654,.36,64), (56,.667,.28,58),
    (60,1.264,.26,56), (63,1.281,.31,59),
    (53,1.892,.48,73), (56,1.909,.45,67), (60,1.919,.44,66),
])

write('drums', midi.Instrument(0, is_drum=True, name='Black Pearl drums'), [
    (36,.017,.16,96), (42,.331,.09,50), (37,.637,.11,91), (40,.641,.10,45),
    (42,.957,.08,54), (36,1.244,.17,85), (42,1.586,.07,49),
    (37,1.886,.10,91), (40,1.891,.10,47),
])
