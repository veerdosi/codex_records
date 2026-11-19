"""Anticipate the original bridge during the last line, using its guitar and kit."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

import numpy as np
from pedalboard import PeakFilter, Reverb
import pretty_midi as midi
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
project = root / 'reaper/Blame Me for Everything'
instruments = root / 'work/shared/composition/instruments'
sys.path.insert(0, str(root / 'work/shared'))
from dsp import SR, db, fade, filt, load

name = 'Blame Me for Everything.rpp'
reference = here / 'Reference.rpp'
if not reference.exists():
    shutil.copy2(project / name, reference)
header, *tracks = re.split(r'(?m)(?=^  <TRACK )', reference.read_text())
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip() + '\n'
media = here / 'Media'
media.mkdir(exist_ok=True)
bridge = float(re.search(r'(?m)^  MARKER 7 (\S+)', header)[1])
beat = 60 / 87
start = 93.33
end = 97.85
n = lambda seconds: round(seconds * SR)
start_sample = n(start)
length = n(end) - start_sample


def track_index(label):
    return next(i for i, track in enumerate(tracks) if f'    NAME "{label}"\n' in track)


def read_source(index):
    track = tracks[index]
    file = re.search(r'(?m)^        FILE "Media/([^"]+)"', track)[1]
    at = n(float(re.search(r'(?m)^      POSITION (\S+)', track)[1]))
    return load(project / 'Media' / file), at


def stereo(x):
    return np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x


def rms_db(x):
    return float(10 * np.log10(max(np.mean(x**2), 1e-12)))


def match(x, level, seconds):
    return x * db(level - rms_db(x[:n(seconds)]))


def at_beat(offset):
    return bridge + offset * beat


def add(track, x, at):
    left = n(at) - start_sample
    right = min(length, left+len(x))
    assert 0 <= left < right
    track[left:right] += x[:right-left]


def new_bus():
    return np.zeros((length, 2), dtype=np.float32)


def attack(x, threshold):
    peak = np.max(abs(x), axis=1)
    return np.flatnonzero(peak >= threshold*peak.max())[0]


# B enters on the tail of B7. E and C-sharp follow on the A and C-sharp
# minor parts. This is an anticipation of the bridge's E–C#–B guitar
# phrase. The low E pickup leads to the existing higher E on the downbeat.
notes = [
    (-4.50, 71, .34, 54, 'B4.flac', -30.0),
    (-3.53, 76, .34, 57, 'E5.flac', -29.8),
    (-2.75, 73, .38, 56, 'C#5.flac', -29.3),
    (-1.52, 71, .51, 60, 'B4.flac', -28.5),
    (-.26, 64, .93, 57, 'E4.flac', -29.8),
]
samples = next((instruments / 'FreePats').glob('SpanishClassicalGuitar-*')) / 'samples'
guitar = new_bus()
score = midi.PrettyMIDI(initial_tempo=87,resolution=960)
guitar_part = midi.Instrument(24,name='Veer | Bridge guitar anticipation')
for when, pitch, duration, velocity, filename, level in notes:
    t = at_beat(when)
    raw = stereo(load(samples / filename))
    onset = attack(raw, .018)
    x = raw[max(0,onset-22):onset+n(duration*beat+.27)]
    x = filt(filt(x,'highpass',190),'lowpass',7700)
    x = fade(x,.0025,.16 if pitch != 64 else .27)
    x = match(x, level, .19)
    add(guitar, x*np.array([1.04,.80],np.float32),t)
    guitar_part.notes.append(midi.Note(velocity,pitch,t-start,t-start+duration*beat))
score.instruments.append(guitar_part)
guitar = Reverb(room_size=.43,damping=.62,wet_level=.15,dry_level=.91,width=.87)(guitar.T,SR).T

# Hold the two common tones over the change of bass. Their release ends
# inside the first bar, where the bridge keys have already taken over.
keys = midi.PrettyMIDI(initial_tempo=87,resolution=960)
keys_part = midi.Instrument(4,name='Veer | E and B across the downbeat')
key_notes = [(-1.54, 52, 2.45, 43),(-.77, 59, 1.63, 42)]
for when, pitch, duration, velocity in key_notes:
    t = at_beat(when)-start
    keys_part.notes.append(midi.Note(velocity,pitch,t,t+duration*beat))
keys.instruments.append(keys_part)
score.instruments.append(keys_part)
keys_midi = here / 'Common tones.mid'
keys.write(str(keys_midi))
keys_wav = here / 'Rhodes raw.wav'
bank = instruments / 'GeneralUser GS/GeneralUser-GS.sf2'
subprocess.run(['fluidsynth','-ni','-g','.50','-r',str(SR),'-F',str(keys_wav),str(bank),str(keys_midi)],
               check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
rhodes = stereo(load(keys_wav))[:length]
rhodes = filt(filt(rhodes,'highpass',200),'lowpass',5100)
span = rhodes[n(at_beat(-1.54)-start):n(at_beat(-.66)-start)]
rhodes *= db(-34.3-rms_db(span))
rhodes = fade(rhodes,.009,.25)
music = guitar+rhodes

# Give the fresh vocal the same space around its formants as before.
vocal, vocal_at = read_source(track_index('21 Savage | Creepin, close vocal'))
aligned = new_bus()
available = min(length, vocal_at + len(vocal) - start_sample)
aligned[:available] = vocal[start_sample - vocal_at:start_sample - vocal_at + available]
vp = filt(filt(aligned, 'highpass',550),'lowpass',1800)
block = n(.025)
power = np.mean(np.pad(vp,((0,-len(vp)%block),(0,0))).reshape(-1,block,2)**2, axis=(1,2))
level = np.sqrt(np.convolve(power,np.ones(5)/5,mode='same'))
activity = np.clip(level / max(np.percentile(level,80),1e-5),0,1)
duck = np.interp(np.arange(length),(np.arange(len(level))+.5)*block,activity)
cut = PeakFilter(cutoff_frequency_hz=1120,gain_db=-3.4,q=.72)(music.T,SR).T
music += (cut-music)*duck[:,None]
music = fade(music,.01,.20)

# Trade two transients on the actual outgoing backbeats. The first clap
# sits inside the existing hit. The next uses the same kit and takes a
# slightly larger share. Both are aligned before mixing with the bed.
kit = next((instruments/'AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
groups = {}
for group in kit.read_text().split('<group>')[1:]:
    key = re.search(r'\bkey=(\d+)\b',group.split('<region>',1)[0])
    if key:
        groups[int(key[1])] = [(int(v),kit.parent/file)
                              for v,file in re.findall(r'hivel=(\d+) sample=([^\r\n]+)',group)]
perc = new_bus()
drum_part = midi.Instrument(0,is_drum=True,name='Veer | Last-line kit handoff')
hits = [
    (94.1134,42,46,-34.5,3000,.125),
    (94.4723,39,53,-29.7,380,.16),
    (94.8292,42,48,-34.0,3000,.135),
    (95.3474,42,52,-32.6,3000,.135),
    (95.8463,39,66,-27.4,380,.175),
]
for t,key,velocity,level,cutoff,duration in hits:
    raw = stereo(load(next(p for limit,p in groups[key] if velocity<=limit)))
    wave = filt(filt(raw,'highpass',cutoff),'lowpass',12300)
    onset = attack(wave,.030)
    first = max(0,onset-15)
    x = fade(wave[first:onset+n(duration)],.001,.041)
    add(perc,match(x,level,.10),t)
    drum_part.notes.append(midi.Note(velocity,key,t-start,t-start+duration))
score.instruments.append(drum_part)
score.write(str(here/'Final line handoff.mid'))

bed_index = track_index('Runaway | Instrumental')
bed, bed_at = read_source(bed_index)
old_bed = bed.copy()
for t, cut_db in [(94.4723,-1.3),(95.8463,-2.0)]:
    i = n(t-.013) - bed_at
    j = n(t+.16) - bed_at
    x = bed[i:j]
    sos = butter(2,[1300,8700],fs=SR,btype='bandpass',output='sos')
    partial = sosfiltfilt(sos,x,axis=0)
    weight = np.interp(np.arange(len(x))/SR,[0,.012,.03,.09,.173],[0,.9,1,.42,0])
    bed[i:j] += partial*(db(cut_db)-1)*weight[:,None]
assert np.array_equal(bed[:n(94.45)-bed_at],old_bed[:n(94.45)-bed_at])
assert np.array_equal(bed[n(96.02)-bed_at:],old_bed[n(96.02)-bed_at:])
bed_name = 'Runaway with final-line kit trade.wav'
sf.write(media/bed_name,bed,SR,'FLOAT')
tracks[bed_index] = re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{bed_name}',tracks[bed_index])


def insert_track(label, file, audio, iid):
    sf.write(media/file,audio,SR,'FLOAT')
    template = tracks[track_index('Veer | Drum room carry')]
    track = re.sub(r'\{[0-9A-F-]{36}\}',lambda _: '{'+str(uuid4()).upper()+'}',template)
    track = re.sub(r'(?m)^(\s+NAME )"[^"]+"$',lambda m: m[1]+f'"{label}"',track)
    for key, value in [('POSITION',f'{start_sample/SR:.12f}'),
                       ('LENGTH',f'{len(audio)/SR:.12f}'),('IID',iid)]:
        track = re.sub(rf'(?m)^      {key} .*$',f'      {key} {value}',track)
    track = re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{file}',track)
    tracks.append(track)


insert_track('Veer | Guitar and keys under Savage', 'Final line common tones.wav', music, 121)
insert_track('Veer | Clap and hat kit trade', 'Final line drum trade.wav', perc, 122)
final = header + ''.join(tracks) + '>\n'
(here/name).write_text(final)
new_files = {p.name for p in media.glob('*.wav')}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda m:str((media if m[1] in new_files else project/'Media')/m[1]),final)
render = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
print(f'First guitar {at_beat(notes[0][0]):.3f}, bridge {bridge:.3f}; outgoing clap anchors 94.472 and 95.846')
