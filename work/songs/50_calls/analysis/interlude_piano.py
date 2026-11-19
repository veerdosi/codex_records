"""A small answer to the hook over the guitar's G and E-minor voicings."""
from pathlib import Path
import pretty_midi as midi

analysis = Path(__file__).resolve().parent
score = midi.PrettyMIDI(initial_tempo=80, resolution=960)
piano = midi.Instrument(0, name='Upright piano')
for pitch, start, duration, velocity in [
    ('D5', 7.51, .63, 44), ('B4', 8.24, .58, 40), ('F#4', 9.78, 1.37, 37),
    ('D5', 24.79, .70, 50), ('B4', 25.54, .71, 44), ('F#4', 27.17, .65, 41), ('E4', 28.47, .95, 36),
    ('B4', 54.78, .73, 46), ('D5', 55.52, .71, 42), ('F#4', 57.19, .58, 40), ('A4', 58.31, .98, 36),
    ('D5', 73.50, .58, 41), ('B4', 74.29, .73, 37), ('F#4', 75.83, 1.21, 34),
    ('G4', 81.14, 1.04, 38), ('E4', 82.43, .91, 32),
]:
    piano.notes.append(midi.Note(velocity, midi.note_name_to_number(pitch), start, start+duration))
score.instruments = [piano]
score.write(str(analysis/'interlude_piano.mid'))
