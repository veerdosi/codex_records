"""Write an original four-bar score and validate the MIDI round-trip."""
from pathlib import Path
import mido
from music21 import key, roman
import pretty_midi as midi

out = Path(__file__).resolve().parent / 'verification'
out.mkdir(exist_ok=True)
tempo = 90
beat = 60 / tempo

def note(track, pitch, start, duration, velocity):
    track.notes.append(midi.Note(velocity, pitch, start*beat, (start+duration)*beat))

score = midi.PrettyMIDI(initial_tempo=tempo, resolution=960)
piano = midi.Instrument(0, name='Piano')
strings = midi.Instrument(48, name='Strings')
flute = midi.Instrument(73, name='Flute')
drums = midi.Instrument(0, is_drum=True, name='Drums')
d_minor = key.Key('d')
for bar, symbol in enumerate(('i7','VI7','iv7','V7')):
    chord = roman.RomanNumeral(symbol, d_minor)
    print(symbol, ' '.join(str(p) for p in chord.pitches))
    start = 4*bar
    root, third, fifth, seventh = (p.midi for p in chord.pitches)
    note(piano, root-12, start, 2.6, 76)
    for index, pitch in enumerate((fifth, seventh, third)):
        note(piano, pitch, start+.35+index*.13, 2.05, 67+index*4)
    note(strings, third, start+.42, 3.2, 46)
    note(strings, seventh, start+.62, 3.08, 44)
    for offset, pitch, velocity in ((0,36,82),(1.01,38,61),(2.53,36,73),(3.01,38,63)):
        note(drums,pitch,start+offset,.14,velocity)
    for index in range(8):
        note(drums,42,start+index*.5+(.044 if index%2 else 0),.09,45+((index*7)%17))
for pitch,start,duration in [(74,1.7,.69),(77,2.5,.74),(81,4.5,1.22),
                             (79,6.5,.89),(77,8.1,1.35),(74,9.8,1.02),
                             (73,12.3,1.19),(74,14.25,1.1)]:
    note(flute,pitch,start,duration,72)
score.instruments = [piano,strings,flute,drums]
score.write(str(out/'instrument_check.mid'))
solo = midi.PrettyMIDI(initial_tempo=tempo, resolution=960)
solo.instruments = [piano]
solo.write(str(out/'piano_check.mid'))
events = [message for message in mido.MidiFile(out/'instrument_check.mid') if message.type == 'note_on' and message.velocity]
assert len(events) == sum(len(track.notes) for track in score.instruments)
print(f'Wrote {len(events)} note events.')
