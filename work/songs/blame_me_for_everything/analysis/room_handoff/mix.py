"""Let the outgoing drum space decay naturally into Veer's bridge."""
import json
from pathlib import Path
import re
import shutil
import sys
from uuid import uuid4

import numpy as np
from pedalboard import Reverb
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
sys.path.insert(0, str(root / 'work/shared'))
from dsp import SR, db, fade, load

name = 'Blame Me for Everything.rpp'
project = root / 'reaper/Blame Me for Everything'
staged_media = here / 'Media'
staged_media.mkdir(exist_ok=True)
reference = here / 'Reference.rpp'
if not reference.exists():
    shutil.copy2(project / name, reference)
rpp = reference.read_text()
header, *tracks = re.split(r'(?m)(?=^  <TRACK )', rpp)
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip() + '\n'
bridge = float(re.search(r'(?m)^  MARKER 7 (\S+)', rpp)[1])
n = lambda seconds: round(seconds * SR)


def find_track(name):
    return next(i for i, track in enumerate(tracks) if f'    NAME "{name}"\n' in track)


def get_media(track):
    path = re.search(r'(?m)^        FILE "Media/([^"]+)"', track)[1]
    time = float(re.search(r'(?m)^      POSITION (\S+)', track)[1])
    return load(project / 'Media' / path), n(time)


def filtered(x, kind, hz):
    sos = butter(2, hz, fs=SR, btype=kind, output='sos')
    return sosfiltfilt(sos, x, axis=0).astype(np.float32)


def rms_db(x):
    return float(10 * np.log10(np.maximum(np.mean(x**2), 1e-12)))


bed, bed_start = get_media(tracks[find_track('Runaway | Instrumental')])
drum_index = find_track('Veer | Handoff Drums')
original_drums, drums_start = get_media(tracks[drum_index])
bridge_sample = n(bridge)
bed_edge = bridge_sample - bed_start
drum_edge = bridge_sample - drums_start

# Capture the upper percussion and room of the last outgoing beat.
# The bass stays on its own track, so the bridge downbeat stays clear.
outgoing = bed[bed_edge - n(.56):bed_edge]
send = fade(filtered(outgoing, 'bandpass', [1050, 7350]), .12, .019)
start_before = n(.077)
decay = n(.51)
feed = np.pad(send, ((0, decay), (0, 0)))
room = Reverb(room_size=.52, damping=.64, wet_level=1., dry_level=0., width=.88)
tail = room(feed.T, SR).T[len(send) - start_before:]
tail = fade(filtered(tail, 'bandpass', [950, 7100]), .048, .27)
tail *= db(-28.8 - rms_db(tail[start_before:start_before + n(.15)]))

# Round off the first bright kit transient and bring its top end back
# over the next eighth note. This leaves the kick and rhythm intact.
length = n(.39)
drums = original_drums.copy()
first = original_drums[drum_edge - n(.09):drum_edge + length + n(.04)]
high = filtered(first, 'highpass', 5300)[n(.09):n(.09) + length]
envelope = np.interp(np.arange(length) / SR,
                     [0., .007, .095, .25, .39], [0., 1., .94, .28, 0.])
drums[drum_edge:drum_edge + length] += high * ((db(-1.25) - 1) * envelope[:, None])
drum_file = 'Bridge drums matched at entry.wav'
tail_file = 'Runaway last-beat room tail.wav'
sf.write(staged_media / drum_file, drums, SR, 'FLOAT')
sf.write(staged_media / tail_file, tail, SR, 'FLOAT')
tracks[drum_index] = tracks[drum_index].replace('Bridge drums with hat handover.wav', drum_file)

# Put the room return on its own editable lane.
track_id, item_id, take_id = ['{' + str(uuid4()).upper() + '}' for _ in range(3)]
tail_at = (bridge_sample - start_before) / SR
tracks.insert(drum_index + 1, f'''  <TRACK {track_id}
    NAME "Veer | Drum room carry"
    VOLPAN 1 0 -1 -1 1
    MAINSEND 1 0
    NCHAN 2
    <ITEM
      POSITION {tail_at:.12f}
      LENGTH {len(tail) / SR:.12f}
      LOOP 0
      FADEIN 1 0 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0 0 1 0 0 0 1 0 0 1 0 0
      NAME "Outgoing drum room into bridge"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      IID 110
      IGUID {item_id}
      GUID {take_id}
      <SOURCE WAVE
        FILE "Media/{tail_file}"
      >
    >
  >
''')

final = header + ''.join(tracks) + '>\n'
(here / name).write_text(final)
new_files = {drum_file, tail_file}
render = re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
                lambda match: str((staged_media if match[1] in new_files else project / 'Media') / match[1]),
                final)
render = re.sub(r'(?m)^  RENDER_FILE .*$', f'  RENDER_FILE "{here}/Master.mp3"', render)
(here / 'Render.rpp').write_text(render)
assert (drums[:drum_edge] == original_drums[:drum_edge]).all()
assert (drums[drum_edge + length:] == original_drums[drum_edge + length:]).all()
assert not np.any(bed[bed_edge:n(bridge + 8 * 60 / 87) - bed_start])
assert len(drums) == len(original_drums)
assert np.isfinite(tail).all()
report = {
    'bridge_downbeat': round(bridge, 6),
    'room_starts': round(tail_at, 6),
    'room_ends': round(tail_at + len(tail) / SR, 6),
    'room_rms_first_150ms_after_downbeat': round(rms_db(tail[start_before:start_before+n(.15)]), 2),
    'kit_rms_first_150ms_after_downbeat': round(rms_db(drums[drum_edge:drum_edge+n(.15)]), 2),
}
(here / 'edit-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(report)
