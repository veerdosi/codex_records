"""Align the selected performances, build the arrangement and prepare REAPER."""
from pathlib import Path
import json
import re
import subprocess
import sys
from uuid import uuid4

import numpy as np
from pedalboard import Compressor, Reverb
import soundfile as sf

song=Path(__file__).resolve().parent
root=song.parents[2]
sys.path.insert(0,str(root/'work/shared'))
from dsp import SR, db, fade, filt, load, stretch

analysis=song/'analysis'
project=root/'reaper/When You Leave'
media=project/'Media'
media.mkdir(parents=True,exist_ok=True)
sources=song/'sources'
stems=song/'stems'
fast=60/87
slow=fast*1.25
first_hook=36*fast
first_end=68*fast
slow_start=first_end+5*fast
savage_start=slow_start+4*slow
savage_end=savage_start+40*slow
kanye=savage_end+4*slow
last_hook=kanye+16*4*fast
last_end=kanye+24*4*fast
duration=last_end+10.45
title='When You Leave'
artist='Kanye West, 21 Savage & Veer'
album='deus complex'


def frames(t):
    return round(t*SR)


def take(x,a,b):
    return x[frames(a):frames(b)].copy()


def add(bus,x,at):
    a=frames(at)
    b=a+len(x)
    assert 0<=a<b<=len(bus),(a,b,len(bus))
    bus[a:b]+=x


def active_db(x):
    n=len(x)//8820
    p=np.mean(x[:n*8820].reshape(n,-1)**2,axis=1)
    return 10*np.log10(p[p>p.max()*.08].mean())


def match(x,target):
    return x*db(target-active_db(x))


def envelope(x,points):
    v=np.interp(np.arange(len(x))/SR,*np.asarray(points).T)
    return x*v[:,None]


def guid():
    return '{'+str(uuid4()).upper()+'}'


source=load(sources/'runaway.wav')
ball=load(stems/'ball_verse_source_vocals.wav')
n=frames(duration)
piano=np.zeros((n,2),np.float32)
runaway=np.zeros_like(piano)
vocal=np.zeros_like(piano)
parts={name:load(analysis/f'Veer {name}.wav') for name in ('Strings','Guitar','Bass','Drums')}
assert all(len(part)==n for part in parts.values())

# The newly written guitar and cello are heard first. The genuine piano
# starts with the tail of its high E motif and continues into the descent.
reveal=take(source,18.190,28.375)
add(piano,fade(reveal,.011,.47)*db(1.1),16*fast)
first_from,first_to=78.20,104.39
first_at=first_hook+(first_from-82.16)
chorus=take(source,first_from,first_to)
add(runaway,fade(match(chorus,-16.0),.28,.17),first_at)

# Trigger short pieces of the same recorded piano at the slower tempo.
# The guitar and the bass move through the chords around the piano.
keys=[(.279,.69),(22.33,.71),(27.18,.73)]
for bar in range(11):
    t=slow_start+bar*4*slow
    i=(bar-1)%4
    if i==3:
        continue
    a,d=keys[i]
    shot=take(source,a,a+d)
    shot=match(fade(filt(shot,'highpass',400),.012,.16),-27)
    add(piano,shot,t+(.50 if bar%2 else .25)*slow)
    if bar in (2,6,10):
        add(piano,shot*.59,t+3.30*slow)

# Cut in the breath after the tag. Keep the complete last line of the verse.
sav_from,sav_to,sav_native=55.225,90.903,55.814
ratio=69/69.6
dry=take(ball,sav_from-52,sav_to-52)
lead=stretch(dry,len(dry)*ratio/SR,'ball_verse_69_6')
lead=filt(lead,'highpass',92)
lead=Compressor(threshold_db=-21,ratio=1.75,attack_ms=10,release_ms=95)(lead.T,SR).T
lead=fade(match(lead,-19.0),.026,.13)
sav_at=savage_start+(sav_from-sav_native)*ratio
add(vocal,lead,sav_at)

# Keep the original reflective verse and the last full chorus together.
# Scale the source gently as the arrangement opens up for the last hook.
k_from,k_to,k_native=258.686,325.13,258.718
last=take(source,k_from,k_to)
last=match(last,-16.4)
last=envelope(last,[(0,.85),(.38,1),(20,1),(26,1.04),(42,1.04),(63,1.08)])
add(runaway,fade(last,.026,.40),kanye+k_from-k_native)

# Strip the recognizable piano back to its tail to close the new guitar motif.
ending=take(source,19.54,26.87)
ending=filt(ending,'lowpass',3700)
room=Reverb(room_size=.69,damping=.64,wet_level=.34,dry_level=.76,width=.87)
ending=room(ending.T,SR).T
add(piano,fade(match(ending,-27.3),.51,2.45),last_end+.65)

for name,gain in [('Strings',-.25),('Guitar',.35),('Bass',-.9),('Drums',-.35)]:
    x=parts[name]
    x*=db(gain)
    if name in ('Strings','Guitar'):
        x[frames(first_at):frames(first_end-.4)]*=db(-2.7)
        x[frames(kanye):frames(last_hook)]*=db(-1)
    if name=='Bass':
        x[:frames(first_end)]*=db(-7)
    parts[name]=x
buses=[
    ('Runaway | Chorus and Kanye verse',runaway),
    ('Runaway | Piano motifs',piano),
    ('21 Savage | Ball w-o You verse',vocal),
    ('Veer | Strings',parts['Strings']),
    ('Veer | Guitar',parts['Guitar']),
    ('Veer | Bass',parts['Bass']),
    ('Veer | Drums',parts['Drums']),
]
backing=sum(x for name,x in buses if x is not vocal)
total=backing+vocal
sf.write(analysis/'Premaster.wav',total,SR,'FLOAT')
print('Sections:',first_hook,slow_start,sav_at,kanye,last_hook,last_end,duration)
print('Savage lead and bed dBFS',round(active_db(take(vocal,sav_at+.3,savage_end)),2),
      round(active_db(take(backing,sav_at+.3,savage_end)),2))

# Compare the same first four bars at both tempos at a matched vocal level.
# Use the stripped Runaway passage as a tempo-fit check only.
trial_verse=take(ball,55.225-52,69.69-52)
alt=stretch(trial_verse,len(trial_verse)*69/87/SR,'ball_trial_87')
test_bed=load(stems/'runaway_bed_source_instrumental.wav')
test_bed=take(test_bed,223.27-214,223.27-214+len(alt)/SR)
n_trial=min(len(alt),len(test_bed))
sf.write(song/'previews/87_bpm_trial.wav',
         fade(match(alt[:n_trial],-18)+match(test_bed[:n_trial],-19),.05,.35),SR,'FLOAT')
sf.write(song/'previews/69_6_bpm_trial.wav',
         fade(take(total,sav_at,sav_at+14.0),.05,.35),SR,'FLOAT')

# Use a verified REAPER render header, but give this song its own timing
# map, metadata, media, tracks and section markers.
rpp=(root/'reaper/50 Calls/50 Calls.rpp').read_text().split('  MARKER ',1)[0]
rpp=re.sub(r'(?m)^  TITLE .*$',f'  TITLE "{title}"',rpp)
rpp=re.sub(r'(?m)^  AUTHOR .*$',f'  AUTHOR "{artist}"',rpp)
rpp=re.sub(r'(?m)^  TEMPO .*$', '  TEMPO 87 4 4 0',rpp)
rpp=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {duration:.10f} 0 1000',rpp)
rpp=re.sub(r'(?m)^  RENDER_FILE .*$', '  RENDER_FILE "When You Leave.mp3"',rpp)
rpp=re.sub(r'(?ms)^  <NOTES .*?^  >\n','',rpp)
rpp=rpp.replace('50 Calls',title).replace('Kanye West, Juice WRLD & Veer',artist)
tempo_points='\n'.join(f'    PT {t:.10f} {bpm} 1 {sig} 0 1'
    for t,bpm,sig in [(0,87,262148),(first_end,87,262149),
                      (slow_start,69.6,262148),(kanye,87,262148)])
rpp=re.sub(r'(?ms)(^  <TEMPOENVEX\n.*?)(^  >)',
    lambda m:re.sub(r'(?m)^    PT .*\n','',m[1])+tempo_points+'\n'+m[2],rpp,count=1)
markers=[
    (0,'Guitar and cello intro'),(16*fast,'Runaway piano'),
    (first_hook,'Kanye | Chorus'),(first_end,'Turn into Savage verse'),
    (savage_start,'21 Savage | Verse'),(savage_end,'Guitar and drums turnaround'),
    (kanye,'Kanye | Later verse'),(last_hook,'Kanye | Final chorus'),
    (last_end,'Guitar and cello outro'),
]
for index,(at,label) in enumerate(markers,1):
    rpp+=f'  MARKER {index} {at:.10f} "{label}" 0 0 1 B {guid()} 0 1\n'
for index,(name,x) in enumerate(buses,1):
    file=f'Track {index:02}.wav'
    i=np.flatnonzero(np.max(abs(x),axis=1)>1e-7)
    a,b=max(0,int(i[0])-64),min(len(x),int(i[-1])+65)
    sf.write(media/file,x[a:b],SR,'FLOAT')
    rpp+=f'''  <TRACK {guid()}
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
rpp+='>\n'
(project/'When You Leave.rpp').write_text(rpp)
absolute=rpp.replace('FILE "Media/',f'FILE "{media}/')
absolute=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{analysis}/Master.mp3"',absolute)
(analysis/'Render.rpp').write_text(absolute)
