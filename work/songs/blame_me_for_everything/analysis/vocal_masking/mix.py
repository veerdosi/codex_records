"""Give the selected lead room and carry an audible backbeat through the bridge."""
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from pedalboard import PeakFilter
import pretty_midi
from scipy.ndimage import gaussian_filter1d
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
project = root / 'reaper/Blame Me for Everything'
name = 'Blame Me for Everything.rpp'
reference = here / 'Reference.rpp'
media = here / 'Media'
media.mkdir(exist_ok=True)
if not reference.exists():
    shutil.copy2(project / name, reference)
header, *tracks = re.split(r'(?m)(?=^  <TRACK )', reference.read_text())
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip() + '\n'
sys.path.insert(0, str(root / 'work/shared'))
from dsp import SR, db, fade, filt, load


def sample(seconds):
    return round(seconds * SR)


def field(chunk, label):
    return float(re.search(rf'(?m)^      {label} (\S+)', chunk)[1])


def rms(audio):
    return float(10 * np.log10(max(np.mean(audio**2), 1e-12)))


def source(name):
    index = next(i for i, t in enumerate(tracks) if f'    NAME "{name}"\n' in t)
    f = re.search(r'(?m)^        FILE "Media/([^"]+)"', tracks[index])[1]
    return index, load(project / 'Media' / f), sample(field(tracks[index], 'POSITION'))


def print_source(index, audio, name):
    sf.write(media / name, audio, SR, 'FLOAT')
    tracks[index] = re.sub(r'(?m)(?<=FILE ")Media/[^"]+', f'Media/{name}', tracks[index])


bridge = float(re.search(r'(?m)^  MARKER 7 (\S+)', header)[1])
bridge_end = float(re.search(r'(?m)^  MARKER 8 (\S+)', header)[1])
_, voice, voice_at = source('21 Savage | Creepin, close vocal')
index, bed, bed_at = source('Runaway | Instrumental')
start = voice_at - bed_at
stop = start + len(voice)
phrase = bed[start:stop].copy()
vocal_body = filt(filt(voice, 'highpass', 390), 'lowpass', 1800)
step = sample(.02)
power = np.mean(np.pad(vocal_body, ((0, -len(vocal_body) % step), (0, 0))).reshape(-1,step,2)**2, axis=(1,2))
env = np.sqrt(gaussian_filter1d(power, 1.5))
reference_level = np.percentile(env[env > env.max() * .075], 65)
activity = np.clip((env/reference_level - .19)*1.65, 0, 1)
t = np.arange(len(voice)) / SR
weight = np.interp(np.arange(len(voice)), (np.arange(len(activity))+.5)*step, activity)
weight *= np.interp(t, [0,.016,len(voice)/SR-.095,len(voice)/SR], [0,1,1,0])
# Pull the centre of the backing down in the range occupied by the
# vocal's formants. Keep the sides, kick, and high percussion intact.
mid = phrase.mean(axis=1, keepdims=True)
notch = PeakFilter(cutoff_frequency_hz=1040, gain_db=-5.2, q=.84)(mid.T, SR).T - mid
body = PeakFilter(cutoff_frequency_hz=490, gain_db=-2.9, q=1.04)(mid.T, SR).T - mid
body_weight = np.interp(t, [0, 14.5, 18.8, 22.8, 30.014], [.30,.35,.62,1,1])
bed[start:stop] = phrase + weight[:,None] * (notch + body*body_weight[:,None])
print_source(index, bed, 'Runaway with vocal space.wav')

drum_index, existing_drums, drum_at = source('Veer | Handoff Drums')
padding = sample(.19)
drum_at -= padding
existing_drums = np.pad(existing_drums, ((padding,0),(0,0)))
for field_name, value in [('POSITION', drum_at), ('LENGTH', len(existing_drums))]:
    tracks[drum_index] = re.sub(rf'(?m)^      {field_name} .*$', f'      {field_name} {value/SR:.12f}', tracks[drum_index])
grid = (bridge_end-bridge) / 8
bridge_local = sample(bridge) - drum_at
times = (np.arange(len(existing_drums))-bridge_local) / SR
drums = existing_drums * np.interp(times, [-.01,0,.055,grid*6.5,grid*7.65],
                                   [1.,1.08,db(1.55),db(1.55),1.])[:,None]
kit = next((root/'work/shared/composition/instruments/AVL Drumkits').glob('BLACK_PEARL*/*.sfz'))
groups = {}
for group in kit.read_text().split('<group>')[1:]:
    key = re.search(r'\bkey=(\d+)\b', group.split('<region>',1)[0])
    if key:
        groups[int(key[1])] = [(int(v), kit.parent / path)
                               for v,path in re.findall(r'hivel=(\d+) sample=([^\r\n]+)', group)]


def hit(key, velocity, level, cutoff, length):
    path = next(p for upper,p in groups[key] if velocity<=upper)
    wave = load(path)
    if wave.shape[1] == 1:
        wave = np.repeat(wave,2,axis=1)
    peak = np.max(abs(wave),axis=1)
    first = np.flatnonzero(peak > peak.max()*.025)[0]
    x = wave[max(0,first-12):first+sample(length)]
    x = filt(filt(x,'highpass',cutoff),'lowpass',12500)
    x = fade(x,.001,.045)
    return x * db(level-rms(x[:sample(.12)]))


# An upbeat snare answer begins under the final word, then the same
# kit takes over. A full snare and short clap reinforce beats two and
# four, where the former rim taps were buried.
hits = [
    (-1.25,42,52,-31.7,3500,.14), (-.26,38,37,-32.7,200,.15),
    (-.12,42,49,-31.2,3400,.13),
    (.98,38,89,-19.9,115,.24), (.99,39,63,-26.2,400,.19),
    (1.47,36,69,-23.6,35,.20), (1.72,42,50,-27.5,3100,.13),
    (2.98,38,96,-19.4,115,.24), (2.99,39,68,-25.7,400,.19),
    (3.51,42,59,-26.7,3000,.14), (3.74,38,43,-31.0,170,.15),
    (4.98,38,88,-20.4,115,.24), (4.99,39,62,-26.5,400,.19),
    (5.73,42,53,-28.1,3100,.13), (6.98,38,97,-20.0,115,.24),
    (6.99,39,66,-26.1,400,.19), (7.36,42,53,-29.7,3200,.13),
]
midi = pretty_midi.PrettyMIDI(initial_tempo=92,resolution=960)
midi_drums = pretty_midi.Instrument(0,is_drum=True,name='Veer | Bridge drum accents')
for beat,key,velocity,level,cutoff,length in hits:
    sample_audio = hit(key, velocity, level, cutoff, length)
    offset = bridge_local + sample(beat * (60/87 if beat<0 else grid))
    end = offset + len(sample_audio)
    assert 0 <= offset and end <= len(drums)
    drums[offset:end] += sample_audio
    t0 = offset / SR
    midi_drums.notes.append(pretty_midi.Note(velocity,key,t0,t0+min(.09,length)))

midi.instruments.append(midi_drums)
midi.write(str(here/'Bridge drum accents.mid'))
print_source(drum_index, drums, 'Bridge drums with snare pocket.wav')
beats = [bridge_local + sample(beat * grid) for beat in range(9)]
print('Bridge drum RMS by beat, old and new')
for x in (existing_drums,drums):
    print([round(rms(x[a:b]),1) for a,b in zip(beats,beats[1:])])
print('Fresh lead timing and samples retained.')
final = header + ''.join(tracks) + '>\n'
(here / name).write_text(final)
files = {x.name for x in media.glob('*.wav')}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda m: str((media if m[1] in files else project/'Media')/m[1]),final)
render = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
