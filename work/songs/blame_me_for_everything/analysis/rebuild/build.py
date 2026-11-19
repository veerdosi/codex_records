"""Assemble the full performances on Runaway's 87 BPM grid for REAPER."""
from pathlib import Path
import json
import re
import sys
from uuid import uuid4

import numpy as np
from pedalboard import Compressor
import soundfile as sf

here = Path(__file__).resolve().parent
song = here.parents[1]
root = song.parents[2]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load, stretch

project = root/'reaper/When You Leave'
media = here/'Media'
media.mkdir(exist_ok=True)
beat = 60/87
bar = 4*beat
duration = 56*bar+1
size = round(duration*SR)

def frames(t):
    return round(t*SR)

def blank():
    return np.zeros((size,2),np.float32)

def clip(x,a,b):
    return x[frames(a):frames(b)].copy()

def add(bus,x,t):
    at = frames(t)
    assert 0<=at<at+len(x)<=len(bus), (t,len(x))
    bus[at:at+len(x)] += x

def active_power(x):
    step = 8820
    q = (x[:len(x)//step*step].reshape(-1,step,2)**2).mean((1,2))
    return q

def active_db(x):
    p = active_power(x)
    return 10*np.log10(p[p>p.max()*.075].mean())

def match(x,target):
    return x*db(target-active_db(x))

def curve(x,points):
    return x*np.interp(np.arange(len(x))/SR,*np.array(points).T).astype(np.float32)[:,None]

def band(x,lo,hi):
    return filt(filt(x,'highpass',lo),'lowpass',hi)

def guid():
    return '{'+str(uuid4()).upper()+'}'

def full_mix_source(a,b):
    with sf.SoundFile(song/'sources/runaway.wav') as source:
        assert source.samplerate==SR
        source.seek(frames(a))
        return source.read(frames(b)-frames(a),dtype='float32')

prior_lead = load(here.parent/'balance/Media/Kanye lead.wav')
bed_source = load(song/'stems/runaway_bed_source_instrumental.wav')
bed_raw = blank()
piano = blank()
kanye = blank()
savage = blank()
parts = {name:load(here/f'Veer {name}.wav') for name in ('Guitar','Strings','Keys','Bass','Drums')}
# Patch a brief separated-voice remnant with the matching musical phase
# from the previous eight bars, holding the kick and bass timing.
patch_a,patch_b = 238.91,240.40
patch = clip(bed_source,patch_a-22.07-214,patch_b-22.07-214)
length = frames(patch_b-214)-frames(patch_a-214)
patch = patch[:length]
a = frames(patch_a-214)
w = fade(np.ones_like(patch),.11,.14)
bed_source[a:a+len(patch)] = bed_source[a:a+len(patch)]*(1-w)+patch*w

def groove(t,source_bar,bars,start_gain=-17,finish_gain=None,fi=.14,fo=.12,overhang=0):
    x = clip(bed_source,source_bar-214,source_bar-214+bars*bar+overhang)
    x = match(x,start_gain)
    if finish_gain is not None:
        x = curve(x,[(0,1),(len(x)/SR,db(finish_gain-start_gain))])
    add(bed_raw,fade(x,fi,fo),t)

# Real Runaway percussion and bass enter behind the high piano, with the
# written parts continuing to play through the last intro bar.
intro = clip(bed_source,225.62-214,225.62-214+4*bar+.20)
intro = match(intro,-17.15)
dark = filt(intro,'lowpass',420)
mid = filt(intro,'lowpass',1800)
span = len(intro)/SR
intro = (curve(dark,[(0,.90),(4.3,.64),(8.2,.13),(span,0)]) +
         curve(mid,[(0,.10),(4.3,.36),(8.2,.67),(span,.0)]) +
         curve(intro,[(0,0),(5.6,0),(8.2,.20),(span,1)]))
add(bed_raw,fade(intro,.45,.22),4*bar)
add(piano,fade(match(full_mix_source(.0,4*bar+.06),-25.5),.02,.19),4*bar)

def kanye_passage(t,anchor,source_start,source_end,lead,lead_anchor,keep_from,keep_to):
    raw = full_mix_source(source_start,source_end)
    direct = clip(lead,source_start-lead_anchor,source_end-lead_anchor)
    direct = direct[:len(raw)]
    raw = raw[:len(direct)]
    # Use the full separated stem to remove vocal carryover at the cut.
    # Only the clean syllable window is returned to the lead track.
    direct = band(direct,74,12000)
    music = raw-direct
    at = t+source_start-anchor
    add(bed_raw,fade(match(music,-16.7),.16,.17),at)
    lead_take = clip(direct,keep_from-source_start,keep_to-source_start)
    add(kanye,fade(lead_take,.028,.070),t+keep_from-anchor)

kanye_passage(8*bar,82.16,82.16,104.40,prior_lead,78.199,82.70,104.13)
groove(16*bar,214.58,16,overhang=.18)
kanye_passage(32*bar,104.24,104.24,126.49,
              load(here/'runaway lead.wav'),103,104.54,126.40)
groove(40*bar,214.58,2,overhang=.18)
groove(42*bar,253.20,2,overhang=.18)
kanye_passage(44*bar,302.86,302.86,325.13,prior_lead,187.86037,303.37,324.88)
groove(52*bar,214.58,2,-17,-29,fo=1.3)
add(piano,fade(match(filt(full_mix_source(19.55,26.6),'lowpass',3400),-31),.70,2.4),53*bar)

# Align the actual opening pickup and 12 native bars without moving
# individual syllables. The fitted source downbeat is the phrase anchor.
sav_start,sav_end = 65.867,98.895
native = 66.459736
ratio = 86.6776733553/87
sav = clip(load(here/'out_for_the_night lead.wav'),sav_start-64.7,sav_end-64.7)
sav = stretch(sav,len(sav)*ratio/SR,'out_for_the_night_87')
sav = band(sav,88,12100)
sav = Compressor(threshold_db=-18,ratio=1.55,attack_ms=14,release_ms=105)(sav.T,SR).T
sav_pos = 18*bar+(sav_start-native)*ratio
add(savage,fade(sav,.017,.063),sav_pos)

shapes = {
    'Strings': [(0,1),(4*bar,.91),(8*bar,.24),(16*bar,.54),(30*bar,.72),
                (32*bar,.43),(40*bar,.87),(44*bar,.64),(52*bar,1.02)],
    'Guitar': [(0,1),(4*bar,.92),(8*bar,.58),(18*bar,.68),(30*bar,1.04),
               (32*bar,.62),(39*bar,.65),(40*bar,1.08),(52*bar,1.04)],
    'Keys': [(0,.69),(31*bar,.76),(39*bar,.84),(52*bar,.78)],
    'Bass': [(0,.81),(4*bar,.53),(5*bar,.48)],
    'Drums': [(0,.70),(4*bar,.57)],
}
for name,shape in shapes.items():
    parts[name] = curve(parts[name],shape)

sections = [
    ('Chorus one',8*bar,16*bar+.15,kanye,1.8),
    ('21 Savage',sav_pos,30*bar,savage,1.75),
    ('Kanye verse',32*bar,40*bar+.12,kanye,1.85),
    ('Final chorus',44*bar,52*bar+.15,kanye,1.65),
]
backing = bed_raw+piano+sum(parts.values())
presence = (400,4800)
report = {}
gain_ranges = [(8*bar,16*bar+.20),(sav_pos-.05,30*bar),
               (32*bar,40*bar+.20),(44*bar,52*bar+.2)]
for (name,a,b,voice,target),(start,end) in zip(sections,gain_ranges):
    v,i = clip(voice,a,b),clip(backing,a,b)
    pp = active_power(band(v,*presence))
    active = pp>pp.max()*.075
    vp,ip = [active_power(band(x,*presence))[active].mean() for x in (v,i)]
    gain = target-10*np.log10(vp/ip)
    voice[frames(start):frames(end)] *= db(gain)
    v = clip(voice,a,b)
    broad = [active_power(band(x,56,12500))[active].mean() for x in (v,i)]
    report[name] = {'time':[round(a,3),round(b,3)],'gain_db':round(gain,2),
                    'presence_ratio_db':target,'broad_ratio_db':round(10*np.log10(broad[0]/broad[1]),2)}

# Leave the hooks an audible lift while keeping the next verse from
# seeming to lose its drum and bass weight as the singer changes.
section_gain = [(0,0),(5*bar,0),(7*bar,.65),(8*bar-.22,.65),
                (8*bar+.26,-1.25),(15*bar,-1.25),(16*bar,-.35),
                (17*bar,0),(18*bar,1.18),(29*bar,1.18),
                (31*bar,.15),(32*bar,0),(42*bar,0),(44*bar,-.8),
                (51*bar,-.8),(52*bar,0)]
section_gain = [(t,db(g)) for t,g in section_gain]
non_piano = curve(backing-piano,section_gain)
for center in (19,51):
    report[f'Backing at {center}s'] = [round(10*np.log10(np.mean(clip(non_piano,t,t+beat)**2)),2)
                                       for t in center+beat*np.arange(-2,3)]
(here/'mix-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)

buses = [
    ('Runaway | Continuous groove',bed_raw),('Runaway | High piano',piano),
    ('Kanye West | Lead',kanye),('21 Savage | Lead',savage),
    *[(f'Veer | {name}',part) for name,part in parts.items()],
]
buses = [(name,curve(x,section_gain)) for name,x in buses]
header = (project/'When You Leave.rpp').read_text().split('  MARKER ',1)[0]
header = re.sub(r'(?m)^    PT (?!0\.0000000000 87).*\n','',header)
header = re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {duration:.10f} 0 1000',header)
rpp = header
markers = [(0,'Guitar and strings'),(4,'Piano and drums enter'),(8,'First chorus'),
           (16,'Guitar answers'),(18,'21 Savage | Out for the Night'),
           (30,'Guitar turnaround'),(32,'Kanye | Opening Runaway verse'),
           (40,'Instrumental lift'),(44,'Final chorus'),(52,'Outro')]
for index,(measure,name) in enumerate(markers,1):
    rpp += f'  MARKER {index} {measure*bar:.10f} "{name}" 0 0 1 B {guid()} 0 1\n'
for index,(name,x) in enumerate(buses,1):
    file = f'Rebuild {index:02d}.wav'
    n = np.flatnonzero(np.max(np.abs(x),axis=1)>1e-7)
    a,b = max(0,int(n[0])-64),min(len(x),int(n[-1])+65)
    sf.write(media/file,x[a:b],SR,'FLOAT')
    rpp += f'''  <TRACK {guid()}
    NAME "{name}"
    VOLPAN 1 0 -1 -1 1
    MAINSEND 1 0
    NCHAN 2
    <ITEM
      POSITION {a/SR:.12f}
      LENGTH {(b-a)/SR:.12f}
      LOOP 0
      FADEIN 1 0 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0 0 1 0 0 0 1 0 0 1 0 0
      NAME "{name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      IID {index}
      IGUID {guid()}
      GUID {guid()}
      <SOURCE WAVE
        FILE "Media/{file}"
      >
    >
  >
'''
rpp += '>\n'
(here/'When You Leave.rpp').write_text(rpp)
render = re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{here}/Master.mp3"',rpp)
(here/'Render.rpp').write_text(render)
sf.write(here/'Premaster.wav',sum(x for _,x in buses),SR,'FLOAT')
