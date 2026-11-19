"""Stage the two-beat verse turnaround while retaining source phrasing."""
from pathlib import Path
import re
import uuid

stage = Path(__file__).resolve().parent
root = stage.parents[4]
project = root / 'reaper/50 Calls/50 Calls.rpp'
original = project.read_text()
extension = 1.5
boundary = 45.0

def update_field(item, field, value):
    result, count = re.subn(
        rf'(?m)^(      {field} )[^\n]*',
        lambda match: f'{match[1]}{value}', item, count=1,
    )
    assert count == 1, field
    return result

def field_value(item, field):
    return float(re.search(rf'(?m)^      {field} ([^ \n]+)', item)[1])

def move_item(item, delta):
    return update_field(item, 'POSITION', f'{field_value(item, "POSITION") + delta:g}')

def fade_item(item, side, seconds):
    return update_field(item, f'FADE{side}', f'1 {seconds:g} 0 1 0 0 0 1 0 0 1 0 0')

def split_item(item, outgoing_end, incoming_source, fade_out, fade_in, item_id):
    start = field_value(item, 'POSITION')
    end = start + field_value(item, 'LENGTH')
    source = field_value(item, 'SOFFS')
    outgoing = update_field(item, 'LENGTH', f'{outgoing_end - start:g}')
    incoming = update_field(item, 'POSITION', f'{incoming_source + extension:g}')
    incoming = update_field(incoming, 'LENGTH', f'{end - incoming_source:g}')
    incoming = update_field(incoming, 'SOFFS', f'{source + incoming_source - start:g}')
    incoming = update_field(incoming, 'IID', item_id)
    for field in ('GUID', 'IGUID'):
        incoming = update_field(incoming, field, '{' + str(uuid.uuid4()).upper() + '}')
    return fade_item(outgoing, 'OUT', fade_out) + fade_item(incoming, 'IN', fade_in)

def edit_item(match):
    item = match[0]
    if 'NAME Verse-Long-Drums.wav' in item:
        return split_item(item, 43.50, 44.225, .056, .022, 146)
    if 'NAME Verse-Long-Bass.wav' in item:
        return split_item(item, 45.0, 44.94, .36, .060, 147)
    if 'NAME Verse-Long-Guitar-clean-vocals.wav' in item:
        return split_item(item, 45.0, 44.94, .42, .060, 148)
    if 'NAME "Interlude piano.wav"' in item:
        return split_item(item, boundary, boundary, .030, .030, 149)
    position = field_value(item, 'POSITION')
    if 'NAME "Kanye verse repaired.wav"' in item and position == 43.74:
        return move_item(item, extension)
    return move_item(item, extension) if position >= boundary else item

def shift_timestamp(match):
    position = float(match[2])
    return f'{match[1]}{position + extension:g}' if position >= boundary else match[0]

def make_absolute(contents):
    return re.sub(r'(?m)^(\s+FILE ")Media/', lambda m: m[1] + str(project.parent / 'Media') + '/', contents)

def render_path(contents, path):
    return re.sub(r'(?m)^  RENDER_FILE .+$', lambda _: f'  RENDER_FILE "{path}"', contents)

def wav_session(contents, stem):
    contents = render_path(make_absolute(contents), stage / f'{stem}.wav')
    contents = re.sub(r'(?m)^  RENDER_NORMALIZE .+$', '  RENDER_NORMALIZE 0 0 0 0 0 1 1', contents)
    contents = re.sub(r'(?m)^  RENDER_STEMS .+$', '  RENDER_STEMS 0', contents)
    contents = re.sub(r'(?ms)^  <RENDER_CFG\n.*?^  >', '  <RENDER_CFG\n    ZXZhdxgAAQ==\n  >', contents)
    (stage / f'{stem}.rpp').write_text(contents)

revised = re.sub(r'(?ms)^    <ITEM\n.*?^    >\n', edit_item, original)
assert revised.count('POSITION 45.24\n') == 1
for pattern in (r'(?m)^(      PT )([0-9.]+)', r'(?m)^(  MARKER \d+ )([0-9.]+)'):
    revised = re.sub(pattern, shift_timestamp, revised)
revised = revised.replace('RENDER_RANGE 0 0 84 ', 'RENDER_RANGE 0 0 85.5 ')
revised = revised.replace('"Kanye | Eight bars"', '"Kanye | Verse and turnaround"')
stage_project = stage / '50 Calls verse restart.rpp'
stage_project.write_text(render_path(make_absolute(revised), stage / 'Revised master.mp3'))
wav_session(original, 'Previous premaster')
