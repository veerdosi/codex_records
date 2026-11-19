"""Build the continuous handoff and the full album arrangement."""
from pathlib import Path
import re
from uuid import uuid4

import numpy as np
from pedalboard import Reverb
from scipy import signal
import soundfile as sf

from audition import BAR, HERE, JOIN, SR, fade, filt, frames, load
import full_mix as original_mix

# The new verse starts six bars later in the source than the earlier hook edit.
VERSE_SOURCE = JOIN + 6 * BAR
DROP = 29 * BAR
# The raw clip contains a short vocal pickup. The first full drum attack
# is 233 ms into it, measured from the aligned instrumental.
DOWNBEAT = DROP + .233
VERSE_END = DOWNBEAT + 12 * BAR
PHASE = DOWNBEAT - DROP
FUTURE_HOOK = 43 * BAR
HOOK_SOURCE = VERSE_SOURCE - 14 * BAR
# Leave the final vowel and consonant release of "percent" with the
# hook. The next phrase starts after the quiet pocket at 66.31.
VOCAL_BOUNDARY = 66.309
SECOND_KANYE = 57 * BAR
REPRISE = 67 * BAR
OUTRO = 75 * BAR
END = 79 * BAR
DURATION = END + 1.05
TITLE = 'YEEZY SEASON 7:12'
ARTIST = 'Kanye West, Future & Veer'
ANALYSIS = HERE/'analysis/extended_mix'
PROJECT = ANALYSIS/'REAPER'
MEDIA = PROJECT/'Media'


def place(bus, sample, at):
    original_mix.place(bus,sample,at)


def trim_envelope(audio, points):
    time = np.arange(len(audio))/SR
    levels = np.interp(time,*np.array(points).T)
    return audio*levels[:,None]


def transition():
    """Keep the string phrase ringing as Future picks up the verse."""
    length=5.1
    out=np.zeros((frames(length),2),np.float32)
    for pitch,at,seconds,volume in [
        (53,0,2.87,.078),(60,.20,2.67,.061),
        (67,.625,1.72,.043),(63,1.255,1.46,.049),(65,1.844,1.58,.058),
        (53,2.663,1.32,.060),(60,2.663,1.49,.050),(67,3.48,1.37,.035),
    ]:
        t = np.arange(frames(seconds))/SR
        hz = 440*2**((pitch-69)/12)
        swell = np.sin(np.pi*np.clip(t/seconds,0,1))**1.1
        for ch,cents in enumerate((-7,7)):
            phase=2*np.pi*hz*2**(cents/1200)*t+.065*np.sin(2*np.pi*5.1*t)
            tone=sum(np.sin(k*phase+(.3*k*ch))*(.62**(k-1)) for k in range(1,8))
            out[frames(at):frames(at)+len(t),ch] += tone*swell*volume
    for at,vol in ((1.847,.039),(2.051,.047),(2.255,.062),(2.663,.085)):
        t=np.arange(frames(.31))/SR
        f=110 if at<2 else 85
        wave=np.sin(2*np.pi*(f*t+2.1*(1-np.exp(-t/.026))))*np.exp(-t/.092)
        wave*=np.minimum(1,t/.002)
        out[frames(at):frames(at)+len(t)] += wave[:,None]*vol
    rev=Reverb(room_size=.59,damping=.59,wet_level=.25,dry_level=.82,width=.95)
    return fade(filt(rev(out.T,SR).T,'highpass',48),.026,.32)


def join_instrumental(bed, instrument, gain, start, end, source_start, overlap):
    """Keep the low end moving while the two harmonically close beds cross."""
    a,b=frames(start-overlap),frames(start)
    incoming=original_mix.aligned_bed(instrument,source_start-overlap,frames(end)-a)*gain
    x,y=bed[a:b],incoming[:b-a]
    fade_shape=np.sin(np.linspace(0,np.pi/2,b-a))[:,None]**2
    if overlap>.20:
        low = signal.butter(2,135,btype='lowpass',fs=SR,output='sos')
        old_low,new_low=(signal.sosfiltfilt(low,z,axis=0) for z in (x,y))
        switch=np.clip((np.linspace(0,1,b-a)-.40)/.23,0,1)[:,None]
        bed[a:b]=(x-old_low)*(1-fade_shape)+(y-new_low)*fade_shape
        bed[a:b]+=old_low*(1-switch)+new_low*switch
    else:
        bed[a:b]=x*(1-fade_shape)+y*fade_shape
    bed[b:frames(end)]=incoming[b-a:]


def vocal_difference(source,instrument,gain,source_start,count):
    album=original_mix.original_at(source,source_start,count)
    backing=original_mix.aligned_bed(instrument,source_start,count)*gain
    return album-backing


def assemble():
    source=load(HERE/'sources/712pm.wav')
    instrument=load(HERE/'sources/712pm_instrumental.wav')
    kanye_main=load(HERE/'stems/facts_vocals.wav')
    kanye_extra=load(HERE/'stems/facts_extra_vocals.wav')
    gain=original_mix.approved_gain(source,instrument)
    n=frames(DURATION)
    bed, kanye, future, authored, fx=[np.zeros((n,2),np.float32) for _ in range(5)]
    opening_end=original_mix.APPROVED_KANYE*BAR
    overlap=.042
    initial=original_mix.aligned_bed(instrument,JOIN+4*BAR,frames(opening_end+overlap))*gain
    initial=original_mix.reduced_bass(initial,[
        (0,.96),(2.4,.87),(4.7,.42),(original_mix.FIRST_HOOK*BAR-.31,0)])
    later_from=JOIN-8*BAR
    a,b=frames(opening_end-overlap),frames(opening_end+overlap)
    before=original_mix.aligned_bed(instrument,later_from-overlap,frames(DROP)-a)*gain
    blend=np.sin(np.linspace(0,np.pi/2,b-a))[:,None]**2
    bed[:a]=initial[:a]
    bed[a:b]=initial[a:b]*(1-blend)+before[:b-a]*blend
    bed[b:frames(DROP)]=before[b-a:]
    # The first Future drum hit belongs to the same native instrumental
    # passage as his verse. Make the source change during Kanye's last lines.
    crossfade_end = 27*BAR+PHASE+.27
    source_offset = VERSE_SOURCE-DROP
    join_instrumental(bed,instrument,gain,crossfade_end,FUTURE_HOOK,
                      crossfade_end+source_offset,.54)
    handoff_start=DROP-2.43
    handoff=bed[frames(handoff_start):frames(DOWNBEAT+1.15)]
    thinned=original_mix.reduced_bass(handoff,[
        (0,0),(1.1,.16),(1.85,.34),(2.48,.34),(2.663,.04),(3.813,0)])
    bed[frames(handoff_start):frames(DOWNBEAT+1.15)]=trim_envelope(thinned,[
        (0,1),(1.3,.92),(2.25,.79),(2.6,.77),(2.663,.97),(3.813,1)])

    # Reconstruct the released mix with only the selected vocal bars audible.
    # Both verse and hook keep their original drum phase and vocal speed.
    verse_count=frames(85.603-VERSE_SOURCE)
    vocal=vocal_difference(source,instrument,gain,VERSE_SOURCE,verse_count)
    vocal=trim_envelope(vocal,[
        (0,0),(VOCAL_BOUNDARY-VERSE_SOURCE,0),(VOCAL_BOUNDARY+.018-VERSE_SOURCE,1),
        (85.535-VERSE_SOURCE,1),(85.603-VERSE_SOURCE,0)])
    place(future,vocal,DROP)
    join_instrumental(bed,instrument,gain,FUTURE_HOOK,END,HOOK_SOURCE,.14)
    hook_count=frames(VOCAL_BOUNDARY-HOOK_SOURCE)
    future_hook=fade(vocal_difference(source,instrument,gain,HOOK_SOURCE,hook_count),.032,.016)
    place(future,future_hook,FUTURE_HOOK)

    hook=original_mix.prepared_kanye(kanye_main,17,27.43,37.22,-16.1)
    for at,throw_gain in ((original_mix.FIRST_HOOK*BAR,.17),(REPRISE,.23)):
        position=at+original_mix.HOOK_OFFSET
        place(kanye,hook,position)
        tail=fade(filt(filt(hook[-frames(.47):],'highpass',315),'lowpass',3400),.023,.13)
        for beats,balance in ((1.5,[.59,1.20]),(3,[1.12,.48])):
            place(fx,tail[:,::-1]*np.array(balance)*throw_gain/beats,
                  position+(len(hook)-len(tail))/SR+beats*BAR/4)
    for sample,at in [
        (original_mix.prepared_kanye(kanye_extra,50,54.53,67.43,-16.4),
         original_mix.KANYE*BAR+original_mix.KANYE_OFFSET),
        (original_mix.prepared_kanye(kanye_main,17,37.47,50.73,-16.4),
         original_mix.APPROVED_KANYE*BAR+original_mix.APPROVED_KANYE_OFFSET),
    ]:
        assert at+len(sample)/SR<DROP
        place(kanye,sample,at)
    second_verse=load(HERE/'stems/facts_second_verse_vocals.wav')
    kanye_start,kanye_end=67.90,81.55
    native_bar=67.64
    ratio=142/147
    additional_at=SECOND_KANYE+PHASE+(kanye_start-native_bar)*ratio
    additional=original_mix.prepared_kanye(second_verse,65,kanye_start,kanye_end,-16.4,
                                           attack=.022,release=.06)
    assert additional_at+len(additional)/SR<REPRISE
    place(kanye,additional,additional_at)
    handoff=transition()
    place(authored,handoff,DROP-2.43)
    # The two bars after the first verse answer the same string phrase.
    response_start=VERSE_END+1.5*BAR/4-2.663
    place(authored,handoff*.67,response_start)
    place(authored,handoff[-frames(1.65):]*.47,REPRISE-.8)

    outro_at=frames(OUTRO+1.5*BAR)
    bed[outro_at:]=original_mix.reduced_bass(bed[outro_at:],[(0,0),(.9,.65),(2.7,.90)])
    room=np.zeros((frames(3.5),2),np.float32)
    room[:frames(.75)]=fade(bed[-frames(2.0):-frames(1.25)],.03,.14)
    rev=Reverb(room_size=.76,damping=.72,wet_level=1,dry_level=0,width=.92)
    fx[-frames(3.05):] += filt(rev(room.T.copy(),SR).T,'highpass',200)[:frames(3.05)]*.28
    for stem in (bed,fx):
        stem[-frames(2.5):]*=np.cos(np.linspace(0,np.pi/2,frames(2.5)))[:,None]**2
    bed=fade(bed,.16,.2)
    assert np.max(np.abs(future[:frames(DROP)+frames(VOCAL_BOUNDARY-VERSE_SOURCE)]))==0
    assert abs(VERSE_END-DOWNBEAT-12*BAR)<1e-8
    print('Future verse downbeat', DOWNBEAT, 'end',VERSE_END)
    print('Future hook',FUTURE_HOOK+PHASE,'new Kanye',additional_at,
          'reprise',REPRISE+PHASE,'duration',DURATION)
    return [
        ('712PM - Instrumental',bed),('Facts - Kanye',kanye),
        ('712PM - Future',future),('Veer - Strings and percussion',authored),
        ('Delay and outro room',fx),
    ]


def guid():
    return '{'+str(uuid4()).upper()+'}'


def write_project(stems):
    # Start from a known-good local REAPER header and keep audio paths relative.
    template=(HERE.parents[2]/'reaper/50 Calls/50 Calls.rpp').read_text()
    header=template.split('  MARKER ',1)[0]
    header=re.sub(r'(?m)^  TITLE .*$',f'  TITLE "{TITLE}"',header)
    header=re.sub(r'(?m)^  AUTHOR .*$',f'  AUTHOR "{ARTIST}"',header)
    header=re.sub(r'(?m)^  TEMPO .*$', '  TEMPO 147 4 4 0',header)
    header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {DURATION:.9f} 0 1000',header)
    header=re.sub(r'(?m)^  RENDER_FILE .*$', '  RENDER_FILE "Yeezy Season 712.mp3"',header)
    header=re.sub(r'(?ms)^  <NOTES .*?^  >\n','',header)
    header=header.replace('50 Calls',TITLE).replace('Kanye West, Juice WRLD & Veer',ARTIST)
    for index,(at,label) in enumerate([(0,'Intro'),(4*BAR,'Kanye | Hook'),
           (12*BAR,'Kanye | Verse'),(DROP-2.43,'Veer | Handoff'),
           (DOWNBEAT,'Future | 12 bars'),(FUTURE_HOOK+PHASE,'Future | Hook'),
           (SECOND_KANYE+PHASE,'Kanye | Second verse'),
           (REPRISE+PHASE,'Kanye | Reprise'),(OUTRO+PHASE,'Outro')],1):
        header+=f'  MARKER {index} {at:.9f} "{label}" 0 0 1 B {guid()} 0 1\n'
    tracks=[]
    for index,(name,audio) in enumerate(stems,1):
        assert np.isfinite(audio).all() and abs(audio).max()<1.4
        active=np.flatnonzero(np.max(np.abs(audio),axis=1)>.000001)
        a=max(0,int(active[0])-64)
        b=min(len(audio),int(active[-1])+65)
        file=f'{name}.wav'
        sf.write(MEDIA/file,audio[a:b],SR,'FLOAT')
        tracks.append(f'''  <TRACK {guid()}
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
''')
    rpp=header+''.join(tracks)+'>\n'
    (PROJECT/'Yeezy Season 712.rpp').write_text(rpp)
    sf.write(ANALYSIS/'Premaster.wav',sum(y for _,y in stems),SR,'FLOAT')
    live=rpp.replace('FILE "Media/',f'FILE "{MEDIA}/')
    live=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{ANALYSIS}/Revised.mp3"',live)
    (ANALYSIS/'Render.rpp').write_text(live)


if __name__=='__main__':
    MEDIA.mkdir(parents=True,exist_ok=True)
    ANALYSIS.mkdir(parents=True,exist_ok=True)
    write_project(assemble())
