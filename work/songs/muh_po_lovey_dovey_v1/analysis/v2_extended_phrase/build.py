"""Add a full instrumental pickup bar before each v2 speed-up."""
from pathlib import Path
import re
from subprocess import run
from uuid import uuid4

import numpy as np
import pretty_midi
from scipy.signal import butter, sosfilt
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
title = 'Muh Pe Lovey Dovey v2'
project = root/'reaper'/title
base = stage/'Before.rpp'
if not base.exists():
    base.write_text((project/(title+'.rpp')).read_text())
original = base.read_text()
beat = 60/82
bar = 4*beat
ramps = (89.193932437720,171.802540106952)
# Insert a bar after each rap. The existing stretched media, tempo
# map and gain automation all move with the original ramp.
end = 213.4076671123+2*bar
def at(t):
    return t+bar*sum(t>=ramp-1e-8 for ramp in ramps)

def value(item,k):
    return re.search(rf'(?m)^      {k} (.*)$',item)[1]

def set_fields(item, fields):
    for k,v in fields.items():
        item = re.sub(rf'(?m)^      {k} .*$',f'      {k} {v}',item)
    return item

def fade(item,k,length):
    f=value(item,k).split()
    f[1]=f'{length:.12f}'
    f[3]='0'
    return set_fields(item,{k:' '.join(f)})

def guid():
    return '{'+str(uuid4()).upper()+'}'

items=re.compile(r'(?ms)^    <ITEM\n.*?^    >$')
prev_pickups = ('Veer - Encore turnaround phrase.wav','Veer - Calm turnaround phrase.wav')
names=['Veer - Encore synth turnaround','Veer - Calm synth turnaround']
# Re-use the native 82 BPM stem playback rate and the bar at the
# same drum phase. Anticipate the upcoming groove with its own E pedal
# while reserving the wider changes for the subsequent tempo ramp.
source_bars=[133.341333333333,202.674666666667]
patch=(root/'work/songs/muh_po_lovey_dovey_v1/analysis/v2_synth_phrase/Media/Veer - Encore turnaround phrase.csd').read_text().split('<CsScore>')[0]
patch=patch.replace('kBrightness expon 1.5,p3,.13','kBrightness expon p7,p3,.18')
patch=patch.replace('aOct oscili .12*aEnv*p5,iHz*2,1','aOct oscili .10*aEnv*p5,iHz*2,1\n  aSub oscili .10*aEnv*p5,iHz*.5,1').replace('aCore+aOct,4650','aCore+aOct+aSub,4900')

# After the opening syncopation, reply a little higher and close
# with a shorter fourth beat. The pitch choices follow E/B with
# G and F-sharp where the backing leaves room for those colors.
phrase=[
    (.058,.23,64,.150,.40,1.70),(.080,.19,71,.086,.61,1.34),
    (.415,.19,67,.164,.60,1.40),(.616,.13,71,.111,.38,1.65),
    (.789,.24,76,.164,.49,1.78),(1.151,.20,71,.143,.59,1.46),
    (1.528,.28,64,.175,.43,1.51),(1.540,.23,76,.096,.63,1.65),
    (1.853,.20,78,.146,.61,1.62),(2.061,.146,76,.095,.40,1.72),
    (2.255,.20,71,.172,.48,1.60),(2.454,.14,67,.112,.60,1.35),
    (2.612,.255,64,.164,.47,1.28),(2.620,.17,71,.083,.55,1.25),
]
for i,name in enumerate(names):
    base=stage/'Media'/name
    colors=[(t,d,64 if i and n==78 else n,a*(1.55 if i else 1.6),
             p if not i else 1-p,b) for t,d,n,a,p,b in phrase]
    if i:
        # A short, low E answers the first chord between the existing
        # bass accents. Leave space before the next live bass attack.
        colors.extend([(.740,.25,52,.143,.50,.37),(.998,.178,52,.135,.50,.32)])
    score=''.join(f'i 1 {t:.6f} {d:.6f} {n} {a:.6f} {p:.5f} {b:.5f}\n'
                  for t,d,n,a,p,b in colors)
    csd=base.with_suffix('.csd')
    csd.write_text(patch+'<CsScore>\nf 1 0 4096 10 1\n'+score+
                   f'f 0 {bar-.020:.12f}\ne\n</CsScore>\n')
    run(['csound','-o',str(base.with_suffix('.wav')),str(csd)],check=True)
    score_midi=pretty_midi.PrettyMIDI(initial_tempo=82,resolution=960)
    voice=pretty_midi.Instrument(81,name='Veer struck synth')
    voice.notes=[pretty_midi.Note(min(127,round(30+a*260)),n,t,t+d) for t,d,n,a,_,_ in colors]
    score_midi.instruments.append(voice)
    score_midi.write(str(base.with_suffix('.mid')))

def move(track, idx):
    def move_item(m):
        item=m[0]
        p,l=float(value(item,'POSITION')),float(value(item,'LENGTH'))
        for n,ramp in enumerate(ramps):
            if prev_pickups[n] in item:
                name=names[n]+'.wav'
                cue=item.replace(prev_pickups[n],name)
                cue=set_fields(cue,{'POSITION':f'{ramp+n*bar:.12f}','LENGTH':f'{bar-.020:.12f}'})
                return fade(cue,'FADEOUT',.012)
        for n,ramp in enumerate(ramps):
            if p<ramp<p+l:
                assert idx in (0,1,2) and ('at source tempo' in item or ' - ramp ' in item)
                if ' - ramp ' in item:
                    return set_fields(item,{'POSITION':f'{p+(n+1)*bar:.12f}'})
                # The outgoing item keeps its existing half-crossfade.
                # Fill the inserted bar using the equivalent beat phase
                # and overlap the incoming item by 20 ms at both edges.
                base_pos=p+n*bar
                bar_pos=ramp+n*bar
                extra=.009755480991
                gain,suffix=value(item,'VOLPAN').split(maxsplit=1)
                ratio=82/90
                bed_gain=[-.05,-.3,-.6][idx] if n==0 else [.25,-.3,-.35][idx]
                bridge=set_fields(item,{
                    'POSITION':f'{bar_pos-extra:.12f}','LENGTH':f'{bar+2*extra:.12f}',
                    'SOFFS':f'{source_bars[n] + (ramp-p)*ratio% (4*60/90) - extra*ratio:.12f}',
                    'NAME':f'"Farebi | {"Drums" if idx==0 else "Bass" if idx==1 else "Music"} under synth"',
                    'LOOP':0,'IID':2000+idx*2+n,'GUID':guid(),'IGUID':guid(),
                    'VOLPAN':f'{float(gain)*10**(bed_gain/20):.12f} {suffix}',
                })
                bridge=fade(fade(bridge,'FADEIN',2*extra),'FADEOUT',2*extra)
                left=set_fields(item,{'POSITION':f'{base_pos:.12f}'})
                return left+'\n'+bridge
        return set_fields(item,{'POSITION':f'{at(p):.12f}'})

    pan=re.compile(r'(?ms)^    <PANENV2\n.*?^    >\n')
    for block in pan.findall(track):
        points=re.findall(r'(?m)^      PT (\S+) (\S+) 0$',block)
        moving=[float(t) for t,g in points if float(g)]
        assert moving and all(any(r<=t<=r+1.5 for r in ramps) for t in moving)
    track=pan.sub('',track)
    track=items.sub(move_item,track)
    track=re.sub(r'(?m)^      PT (\S+) (.*)$',
                 lambda m:f'      PT {at(float(m[1])):.12f} {m[2]}',track)
    if idx not in (0,1,2):
        return track
    env=re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',track)[0]
    pts=[(float(t),float(g)) for t,g in re.findall(r'^      PT (\S+) (\S+) 0$',env,re.M)]
    for i,ramp in enumerate(ramps):
        begin=ramp+i*bar
        finish=begin+bar
        # Carry the old gain into the inserted bar. Ease the old stereo
        # compensation as the full backing enters at its normal width.
        start_gain=next(g for t,g in reversed(pts) if t<begin)
        pts.append((begin-.010,start_gain))
        for t,g in list(pts):
            if finish-.015<=t<=finish+1.47:
                pts.remove((t,g))
                reduction=.95 if idx==0 else .65
                pts.append((t,g*10**(-reduction/20)))
        pts.sort()
    new_points=''.join(f'      PT {t:.12f} {g:.12f} 0\n' for t,g in pts)
    env_header=re.sub(r'(?m)^      PT .*\n','',env).removesuffix('    >')
    return track.replace(env,env_header+new_points+'    >')


header,*tracks=re.split(r'(?m)(?=^  <TRACK )',original)
head=re.sub(r'(?m)^    PT (\S+) (.*)$',lambda m:f'    PT {at(float(m[1])):.12f} {m[2]}',header)
head=re.sub(r'(?m)^(  MARKER \d+ )(\S+)',lambda m:m[1]+f'{at(float(m[2])):.12f}',head)
head=re.sub(r'(?m)^  RENDER_RANGE 0 0 \S+',f'  RENDER_RANGE 0 0 {end:.12f}',head)
# The sparse part under Calm leaves an exposed gap when its bass
# rests. Recall one low hit from Farebi's other turnaround underneath
# the existing snare and hats. The hit is on beat two of both the
# new 82 BPM bar and the existing ramp.
kit_file='Farebi - drums at source tempo.wav'
with sf.SoundFile(project/'Media'/kit_file) as kit:
    assert kit.samplerate==48000
    seek=133.341333333333+(89.193932437720-76.822225120647)*(82/90)%(4*60/90)
    kit.seek(round((seek+.053*82/90)*kit.samplerate))
    hit=kit.read(round(.225*kit.samplerate),dtype='float32')
hit=sosfilt(butter(3,[45,159],btype='bandpass',fs=48000,output='sos'),hit,axis=0)
hit=np.repeat(hit.mean(axis=1,keepdims=True),2,axis=1)
hit[:240]*=np.linspace(0,1,240)[:,None]
hit[-1440:]*=np.linspace(1,0,1440)[:,None]
hit*=10**(-24.3/20)/np.sqrt(np.mean(hit**2))
support='Farebi - Low drum pickup.wav'
sf.write(stage/'Media'/support,hit,48000,'PCM_24')
arrangement=[move(track,i) for i,track in enumerate(tracks)]
calm=ramps[1]+bar
ramp_time=calm+bar
# A linear ramp in BPM advances its first beat by a few milliseconds.
first_ramp_beat=120/(82+(82**2+120*6/(480/85))**.5)
for i,position in enumerate((calm+beat+.050,ramp_time+first_ramp_beat+.050)):
    clip=next(m[0] for m in items.finditer(arrangement[0]) if kit_file in m[0])
    clip=clip.replace(kit_file,support)
    clip=set_fields(clip,{'NAME':'"Farebi | Kick through bass rest"',
        'POSITION':f'{position:.12f}','LENGTH':'.225','SOFFS':0,
        'IID':2100+i,'GUID':guid(),'IGUID':guid(),'VOLPAN':'1 0 1 -1',
        'PLAYRATE':'1 1 0 -1 0 0.0025','LOOP':0})
    clip=fade(fade(clip,'FADEIN',.005),'FADEOUT',.024)
    arrangement[0]=arrangement[0].rstrip().removesuffix('>').rstrip()+'\n'+clip+'\n  >\n'
revised=head+''.join(arrangement)
(stage/'Portable.rpp').write_text(revised)
for label,ext in [('Premaster','wav'),('Drums','wav'),('Master','mp3')]:
    def resolve(m):
        path=next(d/m[2] for d in (stage/'Media',project/'Media') if (d/m[2]).is_file())
        return f'{m[1]}"{path}"'
    document=head+arrangement[0]+'>\n' if label=='Drums' else revised
    text=re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',resolve,document)
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/(label + " stereo")}.{ext}"',text)
    if ext=='wav':
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
