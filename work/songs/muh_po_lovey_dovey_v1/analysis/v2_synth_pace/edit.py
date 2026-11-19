"""Rescore the two synth pickups across the existing 82 BPM bars."""
from pathlib import Path
import re
from subprocess import run

import pretty_midi

stage = Path(__file__).resolve().parent
root = stage.parents[4]
title = 'Muh Pe Lovey Dovey v2'
project = root/'reaper'/title
media = project/'Media'
baseline = stage/'Before.rpp'
if not baseline.exists():
    baseline.write_text((project/(title+'.rpp')).read_text())
original = baseline.read_text()
revised = original

# Seconds from the start of each 82 BPM bar. Accented strikes sit on the
# rendered Farebi kick or snare. The quiet passing notes subdivide the beat
# and the last figure resolves to E before the ramp.
encore = [
    (.069,.105,64,.255),(.070,.090,71,.111),
    (.244,.069,71,.137),(.414,.101,67,.240),(.606,.071,71,.145),
    (.798,.110,76,.258),(.976,.067,71,.144),
    (1.147,.106,74,.210),(1.336,.070,71,.149),
    (1.534,.115,64,.261),(1.535,.095,76,.113),
    (1.707,.065,71,.143),(1.876,.109,78,.235),(2.059,.063,76,.138),
    (2.260,.101,71,.263),(2.434,.085,67,.199),
    (2.526,.063,71,.126),(2.614,.077,74,.174),(2.709,.063,71,.139),
    (2.806,.086,64,.221),(2.807,.081,76,.101),
]
calm = [
    (.150,.102,64,.231),(.150,.086,71,.097),
    (.319,.096,67,.233),(.496,.065,71,.141),(.607,.082,76,.183),
    (.782,.100,71,.210),(.957,.070,64,.134),(1.054,.111,76,.250),
    (1.246,.084,71,.160),(1.426,.086,67,.180),
    (1.608,.070,71,.149),(1.787,.107,76,.250),
    (1.975,.083,74,.177),(2.162,.087,71,.198),
    (2.346,.098,76,.239),(2.515,.068,71,.176),
    (2.610,.061,74,.142),(2.710,.068,71,.166),(2.796,.092,64,.225),
    (.740,.190,52,.164),(.988,.158,52,.148),
]

def change_clips(text, rapper, notes):
    old_name = f'Veer - {rapper} synth turnaround'
    name = f'Veer - {rapper} synth syncopation'
    patch = (media/(old_name+'.csd')).read_text().split('<CsScore>')[0]
    patch = patch.replace('0,.004,1,.017,.68,p3-.021,0', '0,.0035,1,.014,.62,p3-.0175,0')
    events = []
    midi = pretty_midi.PrettyMIDI(initial_tempo=82,resolution=960)
    lead = pretty_midi.Instrument(81,name='Veer syncopated synth')
    for i,(when,length,pitch,gain) in enumerate(sorted(notes)):
        pan = (.46,.53,.51,.47)[i%4] if pitch>55 else .5
        brightness = 1.54 + gain*1.02 if pitch>55 else .36
        # Keep the shorter upper notes audible over the backing.
        if pitch > 55:
            gain *= 1.19
        events.append(f'i 1 {when:.6f} {length:.6f} {pitch} {gain:.5f} {pan:.4f} {brightness:.4f}\n')
        lead.notes.append(pretty_midi.Note(round(28+gain*235),pitch,when,when+length))
    assert max(note.end for note in lead.notes)<2.906829268293
    midi.instruments.append(lead)
    artifact = stage/'Media'/name
    midi.write(str(artifact.with_suffix('.mid')))
    csd = artifact.with_suffix('.csd')
    csd.write_text(patch+'<CsScore>\nf 1 0 4096 10 1\n'+''.join(events)
                   +'f 0 2.906829268293\ne\n</CsScore>\n')
    run(['csound','-o',str(artifact.with_suffix('.wav')),str(csd)],check=True)
    assert text.count(old_name+'.wav')==2
    return text.replace(old_name+'.wav',name+'.wav')

for rapper, notes in [('Encore',encore),('Calm',calm)]:
    revised = change_clips(revised,rapper,notes)

(stage/'Portable.rpp').write_text(revised)
for label,ext in [('Premaster','wav'),('Master','mp3')]:
    def resolve(m):
        src = next(p/m[2] for p in (stage/'Media',media) if (p/m[2]).is_file())
        return f'{m[1]}"{src}"'
    text = re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',resolve,revised)
    text = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if ext=='wav':
        text = re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text = re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text = re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
