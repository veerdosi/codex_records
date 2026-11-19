"""Print the dream-pop backing and stage editable REAPER render projects."""
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

import mido
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import resample_poly
import soundfile as sf

HERE = Path(__file__).resolve().parent
SONG = HERE.parents[1]
ROOT = SONG.parents[2]
TITLE = 'Sunn Raha Hai (Under Glass)'
SESSION = ROOT / 'reaper' / TITLE
SHARED = ROOT / 'work/shared/composition'
MEDIA = HERE / 'Media'
MIDI = SONG / 'midi/dream_pop'
for directory in (MEDIA, MIDI):
    directory.mkdir(exist_ok=True)
sys.path[:0] = [str(SONG), str(HERE.parent / 'shoegaze'), str(SHARED)]
from arrange_shoegaze import BEAT, BPM, SR, SECTIONS, blank, filt, place, voicing
from render_sfizz import render
from arrange import drum, fade

GUITAR = SHARED / 'instruments/Unreal Instruments Standard Guitar/Programs/01-Standard Guitar KSOP.sfz'
BASS = SHARED / 'instruments/Growlybass/growlybass_clean.sfz'
BEFORE = HERE / 'Before.rpp'


def read(path):
    x, rate = sf.read(path, dtype='float32', always_2d=True)
    if rate == 48000:
        return resample_poly(x, 147, 160, axis=0)
    assert rate == SR, rate
    return x


def rms(x):
    return np.sqrt(np.mean(x*x))


def print_audio(name, x):
    path = MEDIA / (name + '.wav')
    sf.write(path, x, SR, 'PCM_24')
    return path


def score_guitar(name, notes):
    path = MIDI / (name + '.mid')
    midi = mido.MidiFile(ticks_per_beat=1920)
    track = midi.add_track()
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
    events = []
    def key(t, pitch, duration, velocity):
        start = max(0, round(t/BEAT*1920))
        end = max(start+1, round((t+duration)/BEAT*1920))
        events.extend([(start, 1, pitch, velocity), (end, 0, pitch, 0)])
    for t, pitch, duration, velocity, switch in notes:
        key(t-.043, switch, .024, 85)
        key(t, pitch, duration, velocity)
    previous = 0
    for tick, on, pitch, velocity in sorted(events):
        track.append(mido.Message('note_on' if on else 'note_off', note=pitch,
                                  velocity=velocity, time=tick-previous))
        previous = tick
    midi.save(path)
    return path


def guitar(name, source, duration, level, echoes):
    x = filt(source, 'bandpass', [185, 5300])
    x = (.84*x.mean(axis=1, keepdims=True)+.16*x)
    x = np.tanh(x*2.65)
    x = filt(x, 'lowpass', 4100)
    x *= 10**(level/20)/np.percentile(
        np.sqrt(np.mean(x[:len(x)//882*882].reshape(-1,882,2)**2, axis=(1,2))), 94
    )
    clip = np.zeros((round(duration*SR), 2), dtype=np.float32)
    place(clip, x, 0., .92, -.28)
    if echoes:
        tail = filt(x, 'bandpass', [450, 3350])
        place(clip, tail, .75*BEAT, .27, .72)
        place(clip, tail, 1.5*BEAT, .15, -.60)
        place(clip, tail, 2.25*BEAT, .08, .60)
    print_audio(name, fade(clip, .008, .17 if echoes else .055))


def make_guitars():
    intro = [(b*BEAT, p, d*BEAT, v, s) for b,p,d,v,s in [
        (.24,73,1.11,66,33), (1.76,72,.29,50,27), (2.55,70,1.0,61,24),
        (4.26,70,1.12,61,24), (6.04,65,.80,56,24), (7.52,66,.22,46,27),
        (8.21,73,1.03,65,33), (9.72,70,.80,58,24), (11.4,66,.33,49,27),
        (12.24,70,1.03,59,24), (13.59,65,.70,54,24), (14.77,60,.37,47,27),
    ]]
    outro = [(b*BEAT,p,d*BEAT,v,s) for b,p,d,v,s in [
        (.28,73,1.28,63,33), (1.82,70,.31,48,27), (2.52,65,1.08,59,24),
        (4.29,70,1.05,60,24), (5.77,66,.32,49,27), (6.54,63,.96,55,24),
        (8.27,73,.68,58,24), (9.12,72,.23,48,27), (9.54,70,2.61,58,33),
        (10.23,65,1.66,46,24),
    ]]
    parts = [
        ('Opening figure', 0., 11.21, -24., True, intro),
        ('Interlude pickup', 93.41, 3.44, -27., True,
         [(.187,72,.14,52,27),(.48,70,.21,56,24),(.795,70,.47,66,33),
          (1.48,65,.28,53,24),(2.27,66,.38,57,24)]),
        ('Verse reply', 107.64, .53, -30., False, [(.247,73,.19,47,24)]),
        ('Lift reply', 144.59, .45, -32., False, [(.064,77,.23,52,24)]),
        ('Refrain reply', 159.59, 1.12, -28., False,
         [(.057,75,.29,59,33),(.61,72,.35,55,24)]),
        ('Closing figure', 171.388433622, 10.66, -25, True, outro),
    ]
    pending = []
    cursor = 0.
    for name, _, duration, level, echoes, notes in parts:
        score_guitar(name, notes)
        if not (MEDIA/(name+'.wav')).exists():
            pending.append((cursor,name,duration,level,echoes,notes))
            cursor += duration+1.
    if pending:
        combined = [(cursor+t,p,d,v,s) for cursor,_,_,_,_,notes in pending for t,p,d,v,s in notes]
        path = MEDIA/'Guitar dry.wav'
        render(score_guitar('Performance print',combined),GUITAR,path,128)
        dry = read(path)
        path.unlink()
        for cursor,name,duration,level,echoes,_ in pending:
            source = dry[round(cursor*SR):round((cursor+duration+.3)*SR)]
            guitar(name,source,duration,level,echoes)
    return [(name,start,duration) for name,start,duration,_,_,_ in parts]


def make_bass():
    midi = mido.MidiFile(SONG / 'midi/shoegaze/Picked bass.mid')
    for event in midi.tracks[0]:
        if event.type == 'note_on':
            # Keep the chorus force, with less exaggerated MIDI velocity jumps.
            event.velocity = round(32 + .63*event.velocity)
    path = MIDI / 'Growlybass.mid'
    midi.save(path)
    dry = MEDIA / 'bass.dry.wav'
    with TemporaryDirectory(dir=HERE) as folder:
        folder = Path(folder)
        # The stock map bottoms out at A1. Expose F1–G#1 using its lowest
        # multisample so the original bass line keeps its octave.
        for directory in BASS.parent.iterdir():
            if directory.is_dir():
                (folder/directory.name).symlink_to(directory,target_is_directory=True)
        extended = folder/'Growlybass low extension.sfz'
        extended.write_text(BASS.read_text().replace('lokey=33','lokey=28',1))
        render(path, extended, dry, 128)
    source = filt(read(dry), 'bandpass', [34, 2650])
    dry.unlink()
    old = read(SESSION / 'Media/Picked bass.wav')
    new = blank()
    mono = source.mean(axis=1, keepdims=True)
    source = .95*mono + .05*source
    place(new, source, 0)
    gains = np.ones(len(new), dtype=np.float32)
    time = np.arange(len(new), dtype=np.float32)/SR
    match_band = lambda x: filt(x, 'bandpass', [46, 195])
    anchors = [(0, 16)] + [(pos,pos+r.stop-r.start) for pos,r in SECTIONS]
    old_low, new_low = match_band(old), match_band(new)
    values = []
    interlude = next(pos for pos,r in SECTIONS if r.section=='guitar interlude')
    for a,b in anchors:
        if a == interlude:
            continue
        a,b = round(a*BEAT*SR),round(b*BEAT*SR)
        ratio = float(rms(old_low[a:b])/max(1e-4,rms(new_low[a:b])))
        assert .5 <= ratio <= 2.5, ratio
        values.append((a,b,ratio))
        gains[a:b] = ratio
    gains = gaussian_filter1d(gains[::441], 14)
    new *= np.interp(time, np.arange(len(gains))*.01, gains)[:,None]
    new = .89*new + .18*filt(new, 'bandpass', [290, 1750])
    # Keep the interlude bass where its existing performance was composed separately.
    a, b = 94.123156, 102.552095
    use_old = np.minimum(np.clip((time-(a-.18))/.18,0,1),
                         np.clip(((b+.20)-time)/.20,0,1))
    new = new*(1-use_old[:,None]) + old*use_old[:,None]
    print('Bass calibration ratios', [round(r,2) if r else None for _,_,r in values])
    print_audio('Growlybass', fade(new, .025, .76))


def make_rhythm():
    kit = blank()
    for pos, region in SECTIONS:
        label = region.section
        if label in ('guitar interlude','outro'):
            continue
        for j in range(0, region.stop-region.start, 4):
            at = pos+j
            index = j//4
            length = min(4, region.stop-region.start-j)
            quiet = label in ('verse', 'verse2')
            chorus = label.startswith('chorus')
            rising = label in ('prechorus lift', 'last prechorus', 'lift')
            if quiet:
                hits = [(0,36,76,0), (2.02,37,48,0), (2.72,36,62,0)]
                bells = [(1.52,42,35,-.26),(3.48,42,43,.22)]
            elif chorus:
                kicks = [(0,36,99,0),(1.74,36,72,0),(2.48,36,88,0)] if index%2==0 else [
                    (0,36,96,0),( .74,36,72,0),(2.71,36,88,0),(3.49,36,68,0)]
                hits = kicks+[(1.01,38,85,0),(3.019,38,93,0),(2.78,40,41,.08)]
                bells = [(x,42, v,p) for x,v,p in [(.50,48,-.30),(1.31,36,.23),
                         (1.52,58,-.21),(2.22,36,.21),(2.51,53,-.19),(3.51,67,.24),(3.80,37,-.23)]]
                if index==0:
                    bells += [(0,51,65,.28)]
            else:
                hits = [(0,36,86,0),(1.73 if index%2 else 1.52,36,56,0),
                        (2.012,38,71 if rising else 62,0),(3.22,36,70,0)]
                bells = [(.54,42,43,-.24),(1.28,42,37,.22),(2.77,42,45,-.2),(3.55,42,50,.25)]
            for offset, key, velocity, pan in hits+bells:
                if offset >= length:
                    continue
                first_entrance = pos==16 and j==0
                if first_entrance and offset < 1 and key != 36:
                    continue
                drum(kit,at+offset,key,velocity-(8 if first_entrance else 0),pan)
    old = read(SESSION / 'Media/Live kit.wav')
    interlude = next(pos for pos,r in SECTIONS if r.section=='guitar interlude')
    outro = next(pos for pos,r in SECTIONS if r.section=='outro')
    kit = filt(kit, 'highpass', 34)
    for a,b in [(interlude-1,interlude+12), (outro,outro+12)]:
        x,y = round(a*BEAT*SR),round(b*BEAT*SR)
        kit[x:y] += fade(old[x:y], .25, .18)
    for start,end in [(4.5,8),(8,11.21)]:
        a,b = round(start*SR),round(end*SR)
        kit[a:b] += fade(old[a:b],.11,.15)*.56
    print_audio('Broken drums', kit*.96)


def make_pad():
    x = blank()
    rng = np.random.default_rng(141)
    sections = {'verse rise': .0070, 'prechorus': .0090, 'prechorus lift': .015,
                'chorus': .023, 'lift': .013, 'last prechorus': .014,
                'chorus2': .025, 'outro': .0085}
    for pos,r in SECTIONS:
        if r.section not in sections:
            continue
        for offset in range(0,r.stop-r.start,2):
            length = min(2,r.stop-r.start-offset)
            _, tones = voicing(r.start+offset)
            # Keep the inner voices in one register across changes.
            notes = [p + 12*(p < 61) - 12*(p > 75) for p in (tones[2],tones[3],tones[4])]
            notes = sorted(set(notes))
            samples = round((length*BEAT+.28)*SR)
            t = np.arange(samples)/SR
            burst = np.zeros((samples,2),dtype=np.float32)
            for idx,pitch in enumerate(notes):
                hz = 440*2**((pitch-69)/12)
                for channel,cents in enumerate((-4.,4.)):
                    phase = rng.uniform(-np.pi,np.pi)
                    a = 2*np.pi*hz*2**(cents/1200)*t+phase
                    amp = .74+.15*np.sin(2*np.pi*(4.1+idx*.63)*t+channel*.85)
                    burst[:,channel] += amp*(np.sin(a)+.16*np.sin(2*a+.15)+.047*np.sin(3*a))
            spread = fade(burst/max(1,len(notes)), .40 if r.section.startswith('chorus') else .54,.39)
            place(x, spread, (pos+offset)*BEAT, sections[r.section])
    pad = filt(x, 'bandpass', [255, 2750])
    print_audio('Drifting chord voices', pad)


def track_chunk(name, clips):
    uid = lambda: '{'+str(uuid4()).upper()+'}'
    chunk = f'  <TRACK {uid()}\n    NAME "{name}"\n    BEAT 0\n    VOLPAN 1 0 -1 -1 1\n    NCHAN 2\n    MAINSEND 1 0\n'
    for clip, start, duration in clips:
        chunk += f'''    <ITEM
      POSITION {start:.12f}
      LENGTH {duration:.12f}
      LOOP 0
      FADEIN 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      IGUID {uid()}
      NAME "{clip}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      GUID {uid()}
      <SOURCE WAVE
        FILE "Media/{clip}.wav"
      >
    >
'''
    return chunk+'  >\n'


def change_volume(track, db):
    return re.sub(r'(?m)^(    VOLPAN )([.\d]+)( .*)$',
                  lambda m: f'{m[1]}{float(m[2])*10**(db/20):.12f}{m[3]}', track, count=1)


def stage(label, header, tracks, wave=True):
    out = 'wav' if wave else 'mp3'
    doc = header+''.join(tracks)+'>\n'
    def resolve(match):
        name = match[2]
        path = next(p/name for p in (MEDIA, SESSION/'Media') if (p/name).is_file())
        return f'{match[1]}"{path}"'
    doc = re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',resolve,doc)
    doc = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{HERE/label}.{out}"',doc)
    if wave:
        doc = re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',doc)
        doc = re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',doc)
        doc = re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',doc)
    (HERE/(label+'.rpp')).write_text(doc)


def projects(clips):
    header,*old=re.split(r'(?m)(?=^  <TRACK )', BEFORE.read_text())
    old[-1] = old[-1].rstrip().removesuffix('>').rstrip()+'\n'
    new = old[:6]
    new[2] = change_volume(new[2], -2.2)
    new[3] = change_volume(new[3], -4.4)
    new[4] = change_volume(new[4].replace('Picked bass','Growlybass'), .8)
    new[5] = new[5].replace('Live kit','Broken drums')
    new[5] = change_volume(new[5], .2)
    length = 182.0673696145
    new += [track_chunk('Picked guitar and delay', clips),
            change_volume(track_chunk('Drifting chord voices',[('Drifting chord voices',0,length)]), 2.7)]
    before_header = header
    header = header.replace('Shoegaze arrangement.', 'Dream-pop arrangement with picked guitar, electric bass and broken drums.')
    header = header.replace('"' + TITLE + '"', '"' + TITLE + ' [Dream Pop]"')
    header = header.replace('Renders/Under Glass.mp3', 'Renders/Under Glass [Dream Pop].mp3')
    (HERE/'Portable.rpp').write_text(header+''.join(new)+'>\n')
    stage('Premaster',header,new)
    stage('Backing',header,new[2:])
    stage('Guitars',header,[new[2],new[3],new[6],new[7]])
    stage('Rhythm',header,new[4:6])
    stage('Master',header,new,wave=False)
    shoegaze_projects(before_header, old, clips)
    stage('Before rhythm',header,old[4:6])


def phrase_rides(track, gestures):
    envelope = re.search(r'(?ms)^    <VOLENV3\n.*?^    >\n',track)
    assert envelope
    pattern = r'(?m)^      PT ([\d.]+) ([\d.]+) 0\n'
    pts = [(float(t),float(g)) for t,g in re.findall(pattern,envelope[0])]
    t0, g0 = zip(*pts)
    times = set(t0)
    for gesture in gestures:
        start,end = gesture[0][0],gesture[-1][0]
        times.update(t for t,_ in gesture)
        times.update(np.linspace(start,end,max(2,round((end-start)/.05))))
    def gain(t):
        delta = sum(np.interp(t,*zip(*gesture),left=0,right=0) for gesture in gestures)
        return np.interp(t,t0,g0)*10**(delta/20)
    newpoints = ''.join(f'      PT {t:.9f} {gain(t):.12f} 0\n' for t in sorted(times))
    new = re.sub(r'(?ms)^      PT .*?(?=^    >)',lambda _:newpoints,envelope[0])
    return track[:envelope.start()]+new+track[envelope.end():]


def shoegaze_projects(header, old, clips):
    header = header.replace('Shoegaze arrangement.', 'Shoegaze arrangement with articulated lead guitar and phrase-shaped swells.')
    revised = old[:6]
    revised[2] = phrase_rides(revised[2],[
        [(0,-1.5),(9.55,-1.5),(10.72,0)],
        [(171.35,0),(172.0,-2.1),(179.12,-1.5),(182.02,0)],
    ])
    revised[3] = phrase_rides(revised[3],[
        [(40.2,0),(40.42,-1.6),(40.77,-.7),(41.28,.7),(41.87,0)],
        [(82.84,0),(83.04,-.9),(83.69,.35),(84.24,0)],
        [(118.59,0),(118.97,-1.45),(119.31,-.48),(119.71,.85),(120.42,0)],
        [(142.48,0),(142.80,-1.3),(143.25,-.24),(143.85,1.05),(144.64,0)],
        [(149.23,0),(149.41,-1.4),(149.78,-.42),(150.16,.56),(150.45,0)],
        [(157.3,0),(157.62,-1.35),(158.19,.40),(158.76,1.15),(159.22,0)],
        [(160.55,0),(160.71,-1.35),(161.02,-1.0),(161.42,0)],
        [(170.40,0),(171.15,-.80),(172.07,-1.2),(180.0,-.85),(182.03,0)],
    ])
    revised[3] = change_volume(revised[3], -.7)
    # The live kit and its original accent pattern anchor this version.
    revised[4] = revised[4].replace('Picked bass','Growlybass')
    revised[4] = change_volume(revised[4], .75)
    # Leave the interlude pickup to the original shoegaze guitar composition.
    revised += [change_volume(track_chunk('Picked guitar answers',
                 [clip for clip in clips if clip[0]!='Interlude pickup']), -1.0)]
    (HERE/'Portable shoegaze.rpp').write_text(header+''.join(revised)+'>\n')
    stage('Shoegaze premaster',header,revised)
    stage('Shoegaze backing',header,revised[2:])
    stage('Shoegaze guitars',header,[revised[2],revised[3],revised[-1]])
    stage('Shoegaze rhythm',header,revised[4:6])
    stage('Shoegaze master',header,revised,wave=False)


if __name__=='__main__':
    if not BEFORE.exists():
        BEFORE.write_bytes((SESSION/(TITLE+'.rpp')).read_bytes())
    clips = make_guitars()
    make_bass()
    make_rhythm()
    make_pad()
    projects(clips)
