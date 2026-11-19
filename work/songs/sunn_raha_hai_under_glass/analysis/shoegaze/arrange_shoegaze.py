"""Score and print the Under Glass shoegaze arrangement for REAPER."""
from pathlib import Path
import subprocess
import sys

import mido
import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter1d
import soundfile as sf

HERE = Path(__file__).resolve().parent
SONG = HERE.parents[1]
sys.path.insert(0, str(SONG))
from arrange import (BASS, BEAT, BPM, GUITAR, ROOTS, SECTIONS, SIZE, SR, VOICES,
                     blank, fade, filt, load, place, rms_envelope, stereo, tame, tone_at, unit)

MEDIA = SONG / 'stems/shoegaze'
MIDI = SONG / 'midi/shoegaze'
MEDIA.mkdir(exist_ok=True)
MIDI.mkdir(exist_ok=True)
RNG = np.random.default_rng(20103)

# Keep the source harmonies that carry long sung notes. Revoice the pedals
# and change the refrains where sustained Bb, C and F allow a new bass line.
CHANGES = {
    4: 'Gb/Bb', 6: 'Gb/Bb', 20: 'Gb/Bb', 22: 'Gb/Bb',
    56: 'Bbm9', 58: 'Bbm9', 60: 'Gbmaj7', 62: 'Gbmaj7',
    64: 'Ab6', 66: 'Ab6', 76: 'Ebm9', 78: 'Ebm9',
    88: 'Bbm9', 90: 'Bbm9', 98: 'Db/F', 102: 'Eb5/C',
    104: 'Bbm9', 106: 'Bbm9', 108: 'Gbmaj7', 110: 'Gbmaj7',
    112: 'Ab6', 114: 'Eb5/C', 116: 'Ab6',
    198: 'Gb/Bb', 200: 'Gb/Bb', 214: 'Gb/Bb', 216: 'Gb/Bb',
    246: 'Bbm9', 248: 'Bbm9', 250: 'Ebm9', 252: 'Ebm9',
    256: 'Db/F', 260: 'Eb5/C',
    262: 'Bbm9', 264: 'Fs', 266: 'Gbmaj7', 268: 'Fs',
    270: 'Ab6', 272: 'Fm7', 274: 'Ab6', 276: 'Fm7',
    278: 'Gbmaj7', 280: 'Gbmaj7', 282: 'Ebm9', 284: 'Ebm9',
    286: 'Fs', 288: 'Fs', 290: 'Fs',
}
EXTENDED = {
    'Bbm9': (34, (46, 53, 61, 65, 72)),
    'Gbmaj7': (30, (42, 49, 58, 65, 73)),
    'Gb/Bb': (34, (46, 54, 61, 65, 73)),
    'Ab6': (32, (44, 51, 60, 65, 70)),
    'Ebm9': (39, (51, 58, 66, 73, 77)),
    'Db/F': (29, (41, 56, 61, 65, 72)),
    'Eb5/C': (36, (48, 55, 58, 63, 65)),
    'Fm7': (29, (41, 48, 56, 63, 72)),
}
SCORE = {key: [] for key in ('Glide left', 'Glide right', 'Harmonics', 'Picked bass')}
DOUBLES = {'chorus', 'chorus2'}
LIFTS = {'prechorus lift', 'last prechorus'}


def note(part, start, pitch, duration, velocity):
    slip = RNG.uniform(-.006, .008) if start > 0 else 0.
    weight = int(np.clip(velocity+RNG.integers(-3, 4), 1, 122))
    SCORE[part].append((start+slip, pitch, duration, weight))


def voicing(source):
    name = CHANGES.get(source, tone_at(source))
    if name in EXTENDED:
        return EXTENDED[name]
    pitches = VOICES[name]
    return ROOTS[name], pitches


def chord(part, at, pitches, duration, velocity, spacing):
    for i, pitch in enumerate(pitches):
        note(part, at+i*spacing, pitch, duration-i*spacing, velocity-i*5)


def write_midi(path, events, program, bend=0.):
    midi = mido.MidiFile(ticks_per_beat=960)
    track = midi.add_track()
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
    track.append(mido.Message('program_change', program=program))
    messages = []
    for start, pitch, length, vel in events:
        down = max(0, round(start*960))
        end = max(down+1, round((start+length)*960))
        messages.extend([(down, 2, mido.Message('note_on', note=pitch, velocity=vel)),
                         (end, 0, mido.Message('note_off', note=pitch))])
    if bend:
        for at in np.arange(0, max(t+d for t,_,d,_ in events)+.1, 1/28):
            drift = np.sin(at*2*np.pi*.49+bend) + .49*np.sin(at*2*np.pi*.91)
            sag = -max(0., np.cos((at-.045)*np.pi))**9
            value = round(4096*(.063*drift+.106*sag))
            messages.append((round(at*960), 1, mido.Message('pitchwheel', pitch=value)))
    previous = 0
    for tick, _, msg in sorted(messages, key=lambda x: x[:2]):
        track.append(msg.copy(time=tick-previous))
        previous = tick
    track.append(mido.MetaMessage('end_of_track', time=3800))
    midi.save(path)


def instrument(part, bank=GUITAR, program=0, bend=0.):
    mid = MIDI/(part+'.mid')
    dry = HERE/(part+' dry.wav')
    write_midi(mid, SCORE[part], program, bend)
    subprocess.run(['fluidsynth', '-ni', '-C', '0', '-R', '0', '-g', '.90',
                    '-T', 'wav', '-O', 'float', '-r', str(SR), '-F', str(dry), str(bank), str(mid)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    out = blank()
    place(out, load(dry), 0.)
    dry.unlink()
    return out


def impulse(seed, decay, length):
    rng = np.random.default_rng(seed)
    size = round(length*SR)
    time = np.arange(size)/SR
    values = rng.standard_normal((size, 2))
    values *= np.exp(-time[:, None]*decay)*np.clip((time-.011)/.026, 0, 1)[:, None]
    values = filt(values, 'bandpass', [390, 4950], 2)
    return (values/np.sqrt((values**2).sum(axis=0))).astype(np.float32)


def wet(audio, seed, decay, length):
    kernel = impulse(seed, decay, length)
    return signal.oaconvolve(audio, kernel, axes=0)[:SIZE].astype(np.float32)


def drive(audio, gain, center, top):
    audio = filt(audio, 'bandpass', [112, 6350], 2)
    audio += .46*filt(audio, 'bandpass', [250, 1730])
    audio = np.tanh(gain*(audio+.16*audio**2))
    audio = np.tanh(1.45*(audio+.07*audio**2))
    audio = filt(audio, 'bandpass', [155, top], 2)
    audio -= .30*filt(audio, 'bandpass', center)
    return audio


def reverse_into(bus, harmonic, at, beats, strength):
    last = round(at*SR)
    count = round(beats*BEAT*SR)
    resonant = harmonic[last:last+count][::-1, ::-1].copy()
    resonant = filt(resonant, 'bandpass', [470, 2900])
    ramp = np.sin(np.linspace(0, np.pi*.5, len(resonant), dtype=np.float32))**2
    resonant *= ramp[:,None]
    place(bus, fade(resonant,.055,.018), at-beats*BEAT, strength)


def write_stem(name, waveform):
    sf.write(MEDIA/(name+'.wav'), waveform, SR, 'PCM_24')


def score():
    # Descending Db–C–Bb figure, supported by a moving bass and a held upper F.
    intro = ((34,(53,58,61,65)),(30,(54,58,61,65)),
             (39,(51,58,65,66)),(29,(53,58,60,65)))
    for i,(root, tones) in enumerate(intro):
        at = i*4
        chord('Glide left', at+.04, tones[:3], 3.58, 46+i*4, .062)
        chord('Glide right', at+.46, tones[1:], 2.98, 43+i*3, .078)
        if i >= 1:
            note('Picked bass', at+.08, root, 3.38, 51+i*3)
    for at,pitch,duration,level in ((.57,73,1.16,66),(2.46,72,1.42,58),(4.24,70,2.07,64),
                                    (7.04,65,.8,53),(8.2,73,1.13,61),(10.44,72,1.37,56),
                                    (12.30,70,2.57,59),(14.86,65,.62,51)):
        note('Harmonics', at, pitch, duration, level)

    drums = []
    def hits(pos, kind, events, length):
        drums.extend((pos+at, kind, vel, pan) for at,vel,pan in events if at<length)

    hits(0,41,[(7.53,42,.10),(12,47,.07),(15.24,53,.11)],16)
    hits(0,51,[(10.25,34,-.28),(14.5,47,-.26)],16)
    for pos,r in SECTIONS:
        if r.section=='guitar interlude':
            continue
        for j in range(0,r.stop-r.start,4):
            start = pos+j
            remaining = min(4,r.stop-r.start-j)
            bar = j//4
            section = r.section
            heavy = section in DOUBLES
            final = section=='chorus2'
            lift = section in LIFTS
            outro = section=='outro'
            soft = section in ('verse','verse2')
            for half in (0,2):
                if half>=remaining:
                    continue
                root, tones = voicing(r.start+j+half)
                # Held open strings and moving upper notes. Drive is wider in refrains.
                power = (tones[0], tones[1], tones[3]) if heavy else (tones[1],tones[3])
                top = (tones[2], tones[3], tones[4]) if heavy or lift else (tones[2],tones[4])
                next_same = half==0 and remaining>2 and voicing(r.start+j+2)==(root,tones)
                if not (half==2 and voicing(r.start+j)==(root,tones) and not heavy):
                    length=3.68 if next_same and not heavy else 1.79
                    if lift and j+4>=r.stop-r.start and half==2:
                        length=1.32
                    strength=(84 if final else 78) if heavy else 63 if lift else 50 if soft else 56
                    if outro:
                        strength=60-6*bar
                    chord('Glide left',start+half+.021,power,length,strength,.018 if heavy else .053)
                    right_start=.044 if heavy else .19
                    chord('Glide right',start+half+right_start,top,length-.09,strength-6,.027)
                    if heavy:
                        chord('Glide left',start+half+1.16,power[:2],.76,strength-13,.022)
                        note('Glide right',start+half+1.37,tones[-1],.51,strength-15)
                if heavy:
                    sequence=((.012,1.05,0), (1.24,.62,0)) if half==0 else ((.015,1.35,0),(1.57,.29,7 if bar%2 else 0))
                elif soft:
                    sequence=((.02,1.46,0),) if half==0 else ((.35,1.36,0),)
                else:
                    sequence=((.021,1.48,0),) if half==0 else ((.08,1.52,0),)
                for at,length,interval in sequence:
                    if interval and not heavy:
                        interval=0
                    note('Picked bass',start+half+at,root+interval,length,
                         94 if final else 88 if heavy else 73 if lift else 61 if soft else 68)
            if (soft and bar%2==1) or outro or heavy and bar%2==1:
                _, tones=voicing(r.start+j)
                if section=='verse2' or outro:
                    phrase=((.42,tones[4],1.18),(1.92,tones[3],.75),(2.90,tones[2]+12,.67))
                else:
                    phrase=((.86,tones[4],.95),(2.72,tones[3]+12,.83))
                for at,pitch,duration in phrase:
                    if at+duration<remaining:
                        note('Harmonics',start+at,pitch,duration,65 if outro else 67 if heavy else 54)
            if outro:
                if bar==0:
                    hits(start,49,[(.0,57,.25)],remaining)
                continue
            if soft:
                if bar==0 and section=='verse':
                    hits(start,36,[(0,56,0.)],remaining)
                    continue
                kicks=[(.0,71,0.),(1.75 if bar%2==0 else 2.66,53,0.)]
                hits(start,37 if bar<3 else 38,[(2.02,62 if bar<3 else 70,0.)],remaining)
                hats=[(.50,36,-.28),(1.52,45,-.28),(2.51,37,-.28),(3.37,46,-.28)]
            elif heavy:
                kicks=[(.0,103,0.),(1.49,76,0.),(2.49,90,0.)] if bar%2==0 else [
                      (.0,102,0.),(.73,69,0.),(2.02,86,0.),(3.52,83,0.)]
                hits(start,38,[(1.014,108,0.),(3.018,115 if final else 108,0.)],remaining)
                hits(start,40,[(2.79,45,.02)] if bar%2 else [(.87,40,.02)],remaining)
                hats=[(k*.5+.012*(k%2),68 if k%2==0 else 49,-.21) for k in range(8)]
                if bar%2==0:
                    hits(start,49 if not final else 57,[(.015,99 if final else 93,.21)],remaining)
            else:
                kicks=[(.0,83,0.),(2.50,75,0.),(3.75,55,0.)] if bar%2 else [
                      (.0,82,0.),(1.75,58,0.),(2.52,73,0.)]
                hits(start,38,[(1.015,78 if lift else 63,0.),(3.02,86 if lift else 75,0.)],remaining)
                hats=[(.49,45,-.26),(1.22,42,-.26),(2.52,55,-.26),(3.48,43,-.26)]
            if lift and j+4>=r.stop-r.start:
                kicks=[kick for kick in kicks if kick[0]<3]
                hats=[hat for hat in hats if hat[0]<3]
                hits(start,45,[(2.51,71,-.14)],remaining)
                hits(start,41,[(2.87,84,.16)],remaining)
            hits(start,36,kicks,remaining)
            hits(start,51 if final else 42,hats,remaining)
    return drums


def render_drums(events):
    from arrange import drum
    kit = blank()
    for at,kind,vel,pan in events:
        drum(kit,at,kind,vel,pan)
    kit=filt(kit,'highpass',34)
    kit += .16*wet(filt(kit,'bandpass',[220,6200]), 41, 16, .32)
    kit = tame(kit,.18,.28,.050)
    return kit


def produce():
    drum_score = score()
    voice = load(SONG/'stems/arrangement/vocal.wav')
    vocal_room = load(SONG/'stems/arrangement/vocal_space.wav')*.64
    clean = instrument('Harmonics',bend=.72)
    clean = unit(filt(clean,'bandpass',[272,6800]), .036)
    clean += .33*wet(clean,17,3.4,1.8)
    for delay,gain in ((.75,.27),(1.5,.15),(2.25,.085),(3,.041)):
        place(clean, filt(clean,'bandpass',[560,3880])[:,::-1], delay*BEAT, gain)
    clean = stereo(clean,1.22)

    guitars = blank()
    for name,bend,grit,mid,top,pan,level in (
            ('Glide left',.4,24,[1020,1930],4300,-.83,.067),
            ('Glide right',2.3,19,[1860,2920],4900,.82,.064)):
        tone=instrument(name,bend=bend)
        tone=unit(drive(tone,grit,mid,top),level)
        room=wet(tone, 21 if pan<0 else 28, 4.1, 1.6)
        # Build a distinct stereo field from two performances and two short rooms.
        place(guitars,tone,0.,.92,pan)
        place(guitars,room,0.,.24,-pan*.47)
    kit = render_drums(drum_score)
    bass = unit(stereo(filt(instrument('Picked bass',bank=BASS,program=34), 'bandpass',[40,2900]),.09),.059)
    bass = tame(bass,.095,.45)
    bass -= .17*filt(bass,'bandpass',[180,340])

    # Long guitar attacks bloom on the grid. A compact pullback before both
    # refrains gives the new downbeats space around the existing vocal.
    times=np.arange(SIZE,dtype=np.float32)/SR
    level=np.ones(SIZE,dtype=np.float32)
    for pos,r in SECTIONS:
        if r.section in DOUBLES:
            attack=pos*BEAT
            reverse_into(clean,guitars,attack,1.45,.56 if r.section=='chorus2' else .47)
            approach=(times>=attack-.52*BEAT)&(times<attack)
            level[approach] = np.maximum(.13, (attack-times[approach])/(.52*BEAT))
    kit *= level[:,None]
    bass *= level[:,None]
    guitars *= (.47+.53*level[:,None])
    first_voice=16*BEAT
    reverse_into(clean,guitars,first_voice,1.2,.46)

    # Reprise the opening guitar figure after the last sung line.
    for pos,r in SECTIONS:
        if r.section=='outro':
            begin=round(pos*BEAT*SR)
            intro=clean[round(.5*BEAT*SR):round(8.5*BEAT*SR)].copy()
            place(clean,fade(intro,.2,1.2),begin/SR+.56,.69)
    vocal_band=filt(voice,'bandpass',[900,3850])
    presence=np.clip((rms_envelope(vocal_band,.13)-.009)*23,0,1)
    protected=filt(guitars,'bandpass',[1150,3500])
    mid=protected.mean(axis=1,keepdims=True)
    guitars -= (.43*mid+.16*(protected-mid))*presence[:,None]
    clean -= .23*filt(clean,'bandpass',[1350,3500])*presence[:,None]

    interlude = next(pos*BEAT for pos,r in SECTIONS if r.section=='guitar interlude')
    for name, stem, gain in [('cleans',clean,1.05),('lead',clean,1.07),('bass',bass,.87),
                             ('drums',kit,.74),('overdrive',guitars,.78)]:
        x=load(SONG/'stems/interlude'/f'{name}.wav')
        place(stem,fade(x,.04,.24),interlude,gain)

    for name,x,fo in [('Glide guitars',guitars,1.25),('Guitar motif and air',clean,1.20),
                      ('Picked bass',bass,1.15),('Live kit',kit,.82),('Shreya lead',voice,.06),
                      ('Vocal room',vocal_room,.30)]:
        write_stem(name,fade(x,.028,fo))
    print(f'Wrote {sum(map(len,SCORE.values()))} MIDI notes, {len(drum_score)} drum hits, {SIZE/SR:.3f} seconds.')


if __name__=='__main__':
    produce()
