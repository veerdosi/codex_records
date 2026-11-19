"""Rebalance the two Under Glass arrangements and stage full REAPER renders."""
from pathlib import Path
import re
import runpy

import numpy as np
from scipy import signal
import soundfile as sf

HERE = Path(__file__).resolve().parent
SONG = HERE.parents[1]
ROOT = SONG.parents[2]
TITLE = 'Sunn Raha Hai (Under Glass)'
SESSION = ROOT/'reaper'/TITLE
TOOLS = runpy.run_path(str(HERE.parent/'dream_pop/arrange.py'))
change_volume = TOOLS['change_volume']
phrase_rides = TOOLS['phrase_rides']
track_chunk = TOOLS['track_chunk']
R = 44100
TAIL_NAME = 'Verse two guitar echo'

FADERS = {
    'Shoegaze': {
        'Shreya lead': -3.4, 'Vocal room': -3.3, 'Guitar motif and air': .95,
        'Glide guitars': 1.15, 'Growlybass': .3, 'Live kit': .45,
        'Picked guitar answers': 1.0,
    },
    'Dream pop': {
        'Shreya lead': -4.25, 'Vocal room': -3.8, 'Guitar motif and air': 1.75,
        'Glide guitars': .45, 'Growlybass': .45, 'Broken drums': .6,
        'Picked guitar and delay': 2.65, 'Drifting chord voices': 5.5,
    },
}


def stage(variant, kind, header, tracks):
    path = HERE/f'{variant} {kind}'
    contents = header+''.join(tracks)+'>\n'
    def resolve(match):
        asset = HERE/match[2] if match[2]==TAIL_NAME+'.wav' else SESSION/'Media'/match[2]
        assert asset.is_file(), asset
        return f'{match[1]}"{asset}"'
    contents = re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',resolve,contents)
    master = kind == 'Master'
    render = path.with_suffix('.mp3' if master else '.wav')
    contents = re.sub(r'(?m)^  RENDER_FILE .*$', f'  RENDER_FILE "{render}"', contents)
    if not master:
        for setting, value in [('NORMALIZE','0 0 0 0 0 0 0'),('STEMS','0')]:
            contents = re.sub(rf'(?m)^  RENDER_{setting} .*$', f'  RENDER_{setting} {value}', contents)
        contents = re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',contents)
    path.with_suffix('.rpp').write_text(contents)


def chorus_rides(offset):
    return [
        [(83.80,0),(84.29,offset),(93.15,offset),(94.1,0)],
        [(149.82,0),(150.32,offset),(170.5,offset),(171.38,0)],
    ]


def guitar_rides(deep):
    # Start the two swells with the sung lifts and taper into the bar.
    # Keep the kick and surrounding rhythmic patterns on the established grid.
    size = 1. if deep else .72
    return [
        [(40.24,0),(40.51,.55*size),(40.98,.78*size),(41.74,0)],
        [(83.04,0),(83.30,.8*size),(83.72,1.9*size),(84.03,1.12*size),(84.42,0)],
        [(118.94,0),(119.18,.72*size),(119.51,1.25*size),(120.36,0)],
        [(142.61,0),(142.84,.72*size),(143.37,1.1*size),(144.23,0)],
        [(149.13,0),(149.43,.8*size),(149.79,2.1*size),(150.12,1.15*size),(150.45,0)],
    ]


def build_pickup_echo():
    # Repeat the last guitar fragment at one eighth note. Its strongest
    # low harmonics are Db and F, shared with the next B-flat minor chord.
    guitar = SESSION/'Media/Guitar motif and air.wav'
    start,end = 101.94,102.45
    x,sr = sf.read(guitar,start=round(start*R),stop=round(end*R),dtype='float32')
    assert sr==R
    sos = signal.butter(2,[205,1630],btype='bandpass',fs=R,output='sos')
    x = signal.sosfilt(sos,x,axis=0)
    t = np.arange(len(x))/R
    envelope = np.sin(np.pi/2*np.minimum(np.clip(t/.144,0,1),
                                         np.clip((t[-1]-t)/.133,0,1)))**2
    x = (.76*x+.24*x[:,::-1])*envelope[:,None]
    sf.write(HERE/(TAIL_NAME+'.wav'),x,R,'PCM_24')
    return (TAIL_NAME,start+.5*60/85.42,len(x)/R)


def edit(variant, pickup):
    title = TITLE + (' [Dream Pop]' if variant=='Dream pop' else '')
    snapshot = HERE/f'{variant} Before.rpp'
    if not snapshot.exists():
        snapshot.write_bytes((SESSION/f'{title}.rpp').read_bytes())
    header,*before = re.split(r'(?m)(?=^  <TRACK )',snapshot.read_text())
    before[-1] = before[-1].rstrip().removesuffix('>').rstrip()+'\n'
    revised = []
    assert len(before)==len(FADERS[variant])
    for track in before:
        name = re.search(r'(?m)^    NAME "([^"]+)"',track)[1]
        track = change_volume(track,FADERS[variant][name])
        if name=='Shreya lead':
            track = phrase_rides(track,chorus_rides(1.25 if variant=='Shoegaze' else .85))
        if name in ('Glide guitars','Guitar motif and air'):
            track = phrase_rides(track,guitar_rides(variant=='Dream pop'))
        revised.append(track)
    revised.append(change_volume(track_chunk(TAIL_NAME,[pickup]), -.8 if variant=='Shoegaze' else .7))
    (HERE/f'{variant} Portable.rpp').write_text(header+''.join(revised)+'>\n')
    stage(variant,'Premaster',header,revised)
    stage(variant,'Backing',header,revised[2:])
    stage(variant,'Master',header,revised)


if __name__=='__main__':
    pickup = build_pickup_echo()
    for version in FADERS:
        edit(version,pickup)
