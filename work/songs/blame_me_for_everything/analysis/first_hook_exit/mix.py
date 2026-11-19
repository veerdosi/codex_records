"""Rebalance the first hook exit, swap the vocal, and quicken the bridge."""
from pathlib import Path
import re
import shutil
import sys
from uuid import uuid4

import numpy as np
import soundfile as sf

from measure import PROJECT, RATE, band, read_tracks, rms, sample, is_vocal, between

here = Path(__file__).resolve().parent
root = here.parents[4]
sys.path.insert(0, str(root / 'work/shared'))
from dsp import fade, load, stretch

name = 'Blame Me for Everything.rpp'
media = here / 'Media'
media.mkdir(exist_ok=True)
reference = here / 'Reference.rpp'
if not reference.exists():
    shutil.copy2(PROJECT / name, reference)
rpp = reference.read_text()
header, *tracks = re.split(r'(?m)(?=^  <TRACK )', rpp)
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip() + '\n'

base_bpm = 87
bridge_bpm = 92
bridge_start = sample(140 * 60 / base_bpm)
old_return = sample(148 * 60 / base_bpm)
new_return = bridge_start + sample(8 * 60 / bridge_bpm)
shift = old_return - new_return
rate = (old_return - bridge_start) / (new_return - bridge_start)


def track_index(label):
    return next(i for i, track in enumerate(tracks) if f'    NAME "{label}"\n' in track)


def track_audio(track):
    file = re.search(r'(?m)^        FILE "Media/([^"]+)"', track)[1]
    return load(PROJECT / 'Media' / file)


def get_field(item, field):
    return re.search(rf'(?m)^      {field} (\S+)', item)[1]


def set_field(item, field, value):
    return re.sub(rf'(?m)^      {field} .*$', f'      {field} {value}', item)


def point(value):
    return f'{value / RATE:.12f}'


def update_media(index, audio, file):
    sf.write(media / file, audio, RATE, 'FLOAT')
    tracks[index] = re.sub(r'(?m)(?<=FILE ")Media/[^"]+', f'Media/{file}', tracks[index])


def gain(x):
    return np.power(10., np.asarray(x) / 20.)


def curve(times, points):
    return np.interp(times, *np.array(points).T)[:, None]


def trim_on_grid(track):
    """Move post-bridge items with their source offsets intact."""
    parts = track.split('    <ITEM\n')
    for i in range(1, len(parts)):
        pos = sample(get_field(parts[i], 'POSITION'))
        if pos >= old_return:
            parts[i] = set_field(parts[i], 'POSITION', point(pos - shift))
    return '    <ITEM\n'.join(parts)


bed_index = track_index('Runaway | Instrumental')
upright_index = track_index('Veer | Upright answer before Savage')
bass_index = track_index('Veer | Bass pickups')
vocal_index = track_index('21 Savage | Creepin, close vocal')

# Keep the low end and the kick where they were. Restore the midrange
# through the first bar of the answer, where the upright used to disappear.
bed = track_audio(tracks[bed_index])
bed_at = sample(get_field(tracks[bed_index], 'POSITION'))
a, b = sample(59.35) - bed_at, sample(65.60) - bed_at
time = (np.arange(a, b) + bed_at) / RATE
mid = band(bed[a:b], [210, 5100], 'bandpass')
support_db = curve(time, [(59.35, 0), (59.85, -.30), (60.11, 0),
                          (60.49, 2.20), (60.82, 2.75), (61.26, 2.65),
                          (61.60, 1.00), (62.20, 1.55), (63.20, 1.95),
                          (64.10, 1.50), (65.05, .70), (65.60, 0)])
bed[a:b] += mid * (gain(support_db) - 1)
# Remove only silence from the long printed bed, then keep the entire
# continuation on its original source samples.
assert not np.any(bed[bridge_start - bed_at:old_return - bed_at])
bed = np.concatenate((bed[:new_return - bed_at], bed[old_return - bed_at:]))
tracks[bed_index] = set_field(tracks[bed_index], 'LENGTH', point(len(bed)))
update_media(bed_index, bed, 'Runaway with balanced hook exit.wav')

# Ease the outgoing pickup and let the outgoing upright decay into the
# answer. Other layers keep the previous envelope to avoid muddying the verse.
bass = track_audio(tracks[bass_index])
t = np.arange(len(bass)) / RATE + sample(get_field(tracks[bass_index], 'POSITION')) / RATE
bass *= gain(curve(t, [(59.20, 0), (59.63, -.48), (60.03, -.88), (60.58, -.65), (60.80, 0)]))
update_media(bass_index, bass, 'Bass pickup into upright answer.wav')

outgoing_index = track_index('Veer | Upright transition phrases')
old_points = '      PT 60.20000000 1 0\n      PT 60.68000000 0 0\n'
new_points = ('      PT 59.36000000 1 0\n'
              '      PT 59.85000000 0.87 0\n'
              '      PT 60.20000000 0.86 0\n'
              '      PT 60.68000000 0.55 0\n'
              '      PT 61.12000000 0.22 0\n'
              '      PT 61.52000000 0 0\n')
assert old_points in tracks[outgoing_index]
tracks[outgoing_index] = tracks[outgoing_index].replace(old_points, new_points)

piano = track_audio(tracks[upright_index])
piano *= gain(curve(np.arange(len(piano)) / RATE,
                    [(0, 1.1), (.50, 1.1), (.81, 1.65), (1.27, 1.1), (2.40, .36), (3.2, 0)]))
update_media(upright_index, piano, 'Upright answer with level ride.wav')

# Use the exact level-matched vocal selected in the comparison.
new_vocal = load(here.parents[1] / 'stems/creepin_album matched lead.wav')
assert len(new_vocal) == sample(get_field(tracks[vocal_index], 'LENGTH'))
update_media(vocal_index, new_vocal, '21 Savage - Creepin album lead.wav')

# Match the faster grid over exactly two bars. Keep the pickup hats at
# their previous positions, and stretch only the new music and its tails.
for part in ('Nylon guitar', 'Electric keys', 'Bass', 'Drums'):
    index = track_index(f'Veer | Handoff {part}')
    track = tracks[index]
    audio = track_audio(track)
    pos = sample(get_field(track, 'POSITION'))
    pickup = bridge_start - pos
    assert pickup >= 0
    main = audio[pickup:]
    duration = len(main) / RATE / rate
    tightened = stretch(main, duration, f'Bridge {part}')
    # The first hit stays on the shared downbeat. A very short taper
    # at the join preserves the existing room and the preceding hats.
    if pickup and part == 'Drums':
        edge = sample(.004)
        tightened[:edge] = fade(tightened[:edge], .004, 0) + fade(main[:edge], 0, .004)
    updated = np.concatenate((audio[:pickup], tightened))
    tracks[index] = set_field(track, 'LENGTH', point(len(updated)))
    update_media(index, updated, f'Bridge {part} at 92 BPM.wav')

tracks = [trim_on_grid(track) for track in tracks]
duration = sample(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)', header)[1])
header = re.sub(r'(?m)^  RENDER_RANGE .*$', f'  RENDER_RANGE 0 0 {point(duration - shift)} 0 1000', header)


def move_marker(match):
    at = sample(match[2])
    if at < old_return:
        return match[0]
    return f'{match[1]}{point(at - shift)}{match[3]}'


header = re.sub(r'(?m)^(  MARKER \d+ )(\S+)( .*)$', move_marker, header)
header = header.replace('Veer | Original bridge, Runaway pocket', 'Veer | Original bridge, 92 BPM')
tempo = '    PT 0.0000000000 87 1 262148 0 1\n'
assert tempo in header
header = header.replace(tempo, tempo + f'    PT {point(bridge_start)} 92 1 0 0 1\n'
                        f'    PT {point(new_return)} 87 1 0 0 1\n')
tempo_block = re.search(r'(?ms)^  <TEMPOENVEX\n.*?^  >', header)[0]
header = header.replace(tempo_block, tempo_block.replace('ACT 0 -1', 'ACT 1 -1'))
final = header + ''.join(tracks) + '>\n'
(here / name).write_text(final)
new_names = {path.name for path in media.glob('*.wav')}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda m: str((media if m[1] in new_names else PROJECT / 'Media') / m[1]), final)
render = re.sub(r'(?m)^  RENDER_FILE .*$', f'  RENDER_FILE "{here}/Master.mp3"', render)
(here / 'Render.rpp').write_text(render)

print('Bridge seconds before and after:', (old_return-bridge_start)/RATE, (new_return-bridge_start)/RATE)
for label, path, extra in [('before', reference, None), ('after', here / name, media)]:
    backing = sum(read_tracks(path, extra, backing_only=True).values())
    mid = band(backing, [180,4000], 'bandpass')
    print(label, 'Backing first bar RMS', round(rms(between(backing,60.69,63.45)),2),
          'midrange transition', [round(rms(between(mid,a,b)),2) for a,b in [(59.8,60.2),(60.2,60.6),(60.6,61.),(61.,61.4)]])
