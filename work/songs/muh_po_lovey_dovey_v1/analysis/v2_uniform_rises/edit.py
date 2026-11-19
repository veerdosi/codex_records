"""Render each upward ramp from a continuous passage of native Farebi stems."""
from pathlib import Path
import re

import numpy as np
from scipy.signal import correlate
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
title = 'Muh Pe Lovey Dovey v2'
project = root / 'reaper' / title
media = project / 'Media'
generated = stage / 'Media'
generated.mkdir(exist_ok=True)

baseline = stage / 'Before.rpp'
if not baseline.exists():
    baseline.write_text((project / (title + '.rpp')).read_text())
before = baseline.read_text()

# Use the existing shared drum-guided stretcher. All three stems follow
# exactly the same sample positions, including through quiet drum fills.
stretcher = (stage.parent / 'source_tempo/build.py').read_text()
start = stretcher.index('def follow_drums(')
end = stretcher.index('def warp_segment(')
rate = 48000
frames = lambda seconds: round(seconds * rate)
exec(compile(stretcher[start:end], 'source_tempo/build.py:follow_drums', 'exec'))

item = re.compile(r'(?ms)^    <ITEM\n.*?^    >\n')


def field(clip, key):
    return re.search(r'(?m)^      ' + key + r' (.*)$', clip)[1]


def put(clip, key, value):
    return re.sub(r'(?m)^      ' + key + r' .*$', lambda _: f'      {key} {value}', clip)


def change(track, stem, artist, rise, landing, codes):
    clips = list(item.finditer(track))
    selected = [m for m in clips if any(f' - ramp {code}.wav' in m[0] for code in codes)]
    assert len(selected) == 3
    first, _, last = selected
    clip_start = float(field(first[0], 'POSITION'))
    clip_end = float(field(last[0], 'POSITION')) + float(field(last[0], 'LENGTH'))
    length = frames(clip_end-clip_start)
    source = f'Farebi - {stem} at source tempo.wav'
    landing_item = next(m[0] for m in clips
                        if source in m[0] and abs(float(field(m[0], 'POSITION'))-landing) < .02)
    source_landing = float(field(landing_item, 'SOFFS')) + (
        landing - float(field(landing_item, 'POSITION'))) * 88/90

    # Integrate the 82→88 BPM line to map output times to source positions.
    # The slope on each side of the ramp matches the adjoining constant clip.
    def source_time(t):
        dt = t-rise
        in_ramp = np.clip(dt, 0, landing-rise)
        musical_time = 82*np.minimum(dt, 0) + 82*in_ramp
        musical_time += 3*in_ramp**2/(landing-rise) + 88*np.maximum(0, t-landing)
        return source_landing + (musical_time-480)/90

    # Give the overlap-add windows real audio on both sides of the edit.
    preroll = .10
    initial = frames(source_time(clip_start-preroll))
    final = frames(source_time(clip_end+preroll+.04))
    backing, sr = sf.read(media / source, start=initial, frames=final-initial, dtype='float32')
    guide, guide_sr = sf.read(media / 'Farebi - drums at source tempo.wav',
                             start=initial, frames=final-initial, dtype='float32')
    assert sr == guide_sr == rate
    positions = np.arange(0, length+2*frames(preroll)+frames(.02), frames(.005)) / rate
    mapped = source_time(positions+clip_start-preroll)-initial/rate
    rendered = follow_drums(backing, guide, mapped, positions, length+2*frames(preroll))
    rendered = rendered[frames(preroll):frames(preroll)+length]

    if artist == 'Calm' and stem == 'drums':
        # The native breakdown has no regular kick. Carry a low, short hit
        # through it so the accelerating beat is audible under its hats.
        hit, hit_sr = sf.read(media / 'Farebi - Low drum pickup.wav', dtype='float32')
        assert hit_sr == rate
        slope = 6/(landing-rise)
        for beat, gain in enumerate((.86, .92, .74, .89, .88, .84, .72, .77)):
            t = rise + 120*beat/(82+np.sqrt(82**2+120*slope*beat))
            index = frames(t+.049-clip_start)
            assert 0 <= index < index+len(hit) <= len(rendered)
            rendered[index:index+len(hit)] += hit*gain
        track = item.sub(lambda m: '' if 'Farebi - Low drum pickup.wav' in m[0]
                         and rise < float(field(m[0], 'POSITION')) < landing else m[0], track)

    name = f'Farebi - {stem} - {artist} continuous rise.wav'
    sf.write(generated / name, rendered, rate, 'FLOAT')
    old_name = f'Farebi - {stem} - ramp {codes[0]}.wav'
    new_clip = first[0].replace(old_name, name)
    new_clip = put(new_clip, 'SOFFS', '0')
    new_clip = put(new_clip, 'LENGTH', f'{clip_end-clip_start:.12f}')
    new_clip = put(new_clip, 'FADEOUT', field(last[0], 'FADEOUT'))
    track = track.replace(first[0], new_clip)
    for m in selected[1:]:
        track = track.replace(m[0], '')
    return track


header, *tracks = re.split(r'(?m)(?=^  <TRACK )', before)
for index, stem in enumerate(('drums', 'bass', 'music')):
    for args in (
        ('Encore', 92.120761706013, 97.767820529542, ('093681', '095991', '098991')),
        ('Calm', 177.656198643537, 183.303257467066, ('180777', '182991', '185991')),
    ):
        tracks[index] = change(tracks[index], stem, *args)

after = header + ''.join(tracks)
(stage / 'Portable.rpp').write_text(after)


def render(label, doc, wave=True):
    def resolve(m):
        source = next(p / m[2] for p in (generated, media) if (p / m[2]).is_file())
        return f'{m[1]}"{source}"'

    text = re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"', resolve, doc)
    out = stage / f'{label}.{"wav" if wave else "mp3"}'
    text = re.sub(r'(?m)^  RENDER_FILE .*$', f'  RENDER_FILE "{out}"', text)
    if wave:
        text = re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0', text)
        text = re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0', text)
        text = re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)', r'\g<1>    ZXZhdxgAAQ==\n\2', text)
    (stage / f'{label}.rpp').write_text(text)


render('Premaster', after)
render('Master', after, wave=False)
render('Drums', header+tracks[0]+'>\n')
render('OldDrums', header+re.split(r'(?m)(?=^  <TRACK )', before)[1]+'>\n')
