"""Replace the custom bridge with the last two bars of Runaway's final hook."""
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from pedalboard import PeakFilter
from scipy.signal import butter, sosfiltfilt
import soundfile as sf

here = Path(__file__).resolve().parent
root = here.parents[4]
project = root / 'reaper/Blame Me for Everything'
name = 'Blame Me for Everything.rpp'
reference = here / 'Reference.rpp'
if not reference.exists():
    shutil.copy2(project/name,reference)
header,*tracks = re.split(r'(?m)(?=^  <TRACK )',reference.read_text())
tracks[-1] = tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
media = here / 'Media'
media.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, load

n = lambda seconds: round(float(seconds)*SR)
bridge = n(re.search(r'(?m)^  MARKER 7 (\S+)',header)[1])
old_return = n(re.search(r'(?m)^  MARKER 8 (\S+)',header)[1])
new_return = bridge+n(8*60/87)
extension = new_return-old_return


def clock(samples):
    return f'{samples/SR:.12f}'


def rms_db(x):
    return float(10*np.log10(max(np.mean(x*x),1e-12)))


def band(y, limits):
    sos = butter(2,limits,fs=SR,btype='bandpass',output='sos')
    return sosfiltfilt(sos,y,axis=0)


def get(chunk, field):
    return re.search(rf'(?m)^      {field} (\S+)',chunk)[1]


def set_field(chunk, field, value):
    return re.sub(rf'(?m)^      {field} .*$',f'      {field} {value}',chunk)


def track_name(chunk):
    return re.search(r'(?m)^    NAME "([^"]+)"',chunk)[1]


custom_tracks = {
    'Veer | Handoff Nylon guitar', 'Veer | Handoff Electric keys',
    'Veer | Handoff Bass', 'Veer | Handoff Drums', 'Veer | Drum room carry',
    'Veer | Guitar and keys under Savage', 'Veer | Clap and hat kit trade',
}
assert custom_tracks <= {track_name(chunk) for chunk in tracks}
tracks = [chunk for chunk in tracks if track_name(chunk) not in custom_tracks]
bed_index = next(i for i,c in enumerate(tracks) if track_name(c)=='Runaway | Instrumental')
bed_at = n(get(tracks[bed_index],'POSITION'))
# Use the backing before the last attempt's custom-kit edits. It already
# has the approved first handoff and the spectral space around Savage.
bed = load(project/'Media/Runaway with vocal space.wav')
start = bridge-bed_at
old_end = old_return-bed_at
assert not np.any(bed[start:old_end])

# Original E resolves back in the arrangement at 4:18.72 source time.
# Use the Amaj7 and B7 bars from the original final hook as its lead-in.
source_anchor = 319.42
source_offset = 315.75
pre, tail = n(.082),n(.068)
end = new_return-bed_at
length = end-start
source_index = n(source_anchor-source_offset)
instrumental = load(here/'runaway backing.wav')
pick = instrumental[source_index-pre:source_index+length+tail].copy()
assert len(pick)==pre+length+tail
# Bring the lifted section to the level of the groove at the return.
# The chord and drum tone are otherwise from the original recording.
old_level = rms_db(band(bed[start-n(3.1):start-n(.11)],[45,12000]))
pick_level = rms_db(band(pick[pre:pre+length],[45,12000]))
gain = np.clip(old_level-pick_level+.25,-12,6)
pick *= db(gain)
# A shallow low-mid correction keeps the vocal's previous body separate
# from the wider chord voicing as the instrumental takes over.
eq = PeakFilter(cutoff_frequency_hz=255,gain_db=-.9,q=.72)
pick = eq(pick.T,SR).T

bed = np.concatenate((bed[:start],np.zeros((length,2),np.float32),bed[old_end:]))
# The first chord speaks at its native downbeat. The pickup is only a
# fraction of a beat and uses the original musical decay on both sides.
a,b = start-pre,end+tail
incoming = fade(pick,.073,.062)
old = bed[a:b].copy()
from_old = np.ones((len(old),1),np.float32)
from_old[:pre] = 1-fade(np.ones((pre,1),np.float32),.075,0)
from_old[pre+length:] = fade(np.ones((tail,1),np.float32),.049,0)
bed[a:b] = old*from_old+incoming
filename='Runaway with original chord lift.wav'
sf.write(media/filename,bed,SR,'FLOAT')
tracks[bed_index]=set_field(tracks[bed_index],'LENGTH',clock(len(bed)))
tracks[bed_index]=re.sub(r'(?m)(?<=FILE ")Media/[^"]+',f'Media/{filename}',tracks[bed_index])

for index,chunk in enumerate(tracks):
    items=chunk.split('    <ITEM\n')
    for i,item in enumerate(items[1:],1):
        pos=n(get(item,'POSITION'))
        if pos>=old_return:
            items[i]=set_field(item,'POSITION',clock(pos+extension))
    tracks[index]='    <ITEM\n'.join(items)

duration=n(re.search(r'(?m)^  RENDER_RANGE 0 0 (\S+)',header)[1])
header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {clock(duration+extension)} 0 1000',header)
header=re.sub(r'(?m)^    PT (?:96\.551723356009 92|101\.769115646258 87) 1 0 0 1\n','',header)
assert ' 92 1 0 0 1' not in header
def move_marker(m):
    at=n(m[2])
    return m[0] if at<old_return else f'{m[1]}{clock(at+extension)}{m[3]}'
header=re.sub(r'(?m)^(  MARKER \d+ )(\S+)( .*)$',move_marker,header)
header=header.replace('Veer | Original bridge, 92 BPM','Runaway | Original Amaj7–B7 lift')
final=header+''.join(tracks)+'>\n'
(here/name).write_text(final)
render=re.sub(r'(?m)(?<=FILE ")Media/([^"]+)',
              lambda m:str((media if m[1]==filename else project/'Media')/m[1]),final)
render=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',render)
(here/'Render.rpp').write_text(render)
report={'source_start':source_anchor,'source_end':source_anchor+length/SR,
        'bridge_start':bridge/SR,'kanye_downbeat':new_return/SR,'tempo':87,
        'source_gain_db':round(float(gain),2),'outgoing_rms_db':round(old_level,2),
        'turnaround_rms_db':round(rms_db(band(bed[start:end],[45,12000])),2)}
(here/'edit-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
