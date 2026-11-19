"""Give the pre-ramp synth answer a clear attack and carry the backing through."""
from pathlib import Path
import math
import re
from subprocess import run
import pretty_midi

stage=Path(__file__).resolve().parent
root=stage.parents[4]
project=root/'reaper/Muh Pe Lovey Dovey v2'
base=stage/'Before.rpp'
if not base.exists():
    base.write_text((project/(project.name+'.rpp')).read_text())
original=base.read_text()
header,*tracks=re.split(r'(?m)(?=^  <TRACK )',original)

def envelope(track, changes):
    old=re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',track)[0]
    points=[(0.,0.), *changes, (213.4076671123,0.)]
    data=''.join(f'      PT {t:.12f} {10**(g/20):.12f} 0\n' for t,g in points)
    new=re.sub(r'(?m)^      PT .*\n','',old)
    return track.replace(old,new.removesuffix('    >')+data+'    >')

def swell(begin,pan_end,amount):
    return [(begin-.38,0),(begin-.10,amount*.60),(begin,amount),
            (pan_end-.06,amount),(pan_end+.42,0)]

a,b=89.193932437720,171.802540106952
e,f=90.653729504753,173.262337173985
tracks[0]=envelope(tracks[0],swell(a,e,1.6)+swell(b,f,1.9)+[
    (177.85,0),(178.13,1.1),(179.12,1.5),(179.58,0)])
tracks[1]=envelope(tracks[1],swell(a,e,1.4)+swell(b,f,1.65)+[
    (174.38,0),(177.03,-.3),(177.74,-.8),(178.12,-1.15),(179.11,-1.15),
    (179.49,0)])
tracks[2]=envelope(tracks[2],swell(a,e,1.05)+swell(b,f,1.4)+[
    (177.88,0),(178.13,1.6),(179.12,2.0),(179.58,0)])

# These pitches anticipate the root and fifth of the incoming groove.
# The low strike answers with a brighter upper note at the sixteenth.
patch=(project/'Media/Veer - Encore pre-ramp synth.csd').read_text().split('<CsScore>')[0]
patch=patch.replace('4200,p3,620','5100,p3,980').replace('p5*2.15','p5*3.65')
duration=60/82/2-.026
notes=[(.006,.113,71,.185,.37),(.010,.091,64,.098,.48),
       (.176,.136,76,.178,.61),(.179,.108,71,.080,.50)]
for rapper in ('Encore','Calm'):
    old=f'Veer - {rapper} pre-ramp synth'
    stem=f'Veer - {rapper} synth pickup'
    csd=stage/'Media'/f'{stem}.csd'
    score=''.join(f'i 1 {t:.6f} {d:.6f} {p} {g:.6f} {pan:.6f}\n'
                  for t,d,p,g,pan in notes)
    csd.write_text(patch+'<CsScore>\nf 1 0 4096 10 1\n'+score+
                   f'f 0 {duration:.12f}\ne\n</CsScore>\n')
    run(['csound','-o',str(csd.with_suffix('.wav')),str(csd)],check=True)
    midi=pretty_midi.PrettyMIDI(initial_tempo=82,resolution=960)
    voice=pretty_midi.Instrument(81,name='Veer pulse synth')
    voice.notes=[pretty_midi.Note(round(min(127,g*485+27)),p,t,t+d)
                 for t,d,p,g,_ in notes]
    midi.instruments.append(voice)
    midi.write(str(csd.with_suffix('.mid')))
    assert tracks[-1].count(old)==2
    tracks[-1]=tracks[-1].replace(old,stem)

revised=header+''.join(tracks)
(stage/'Portable.rpp').write_text(revised)
for label,wav,text in [('Premaster',True,revised),('Master',False,revised),
                       ('Before backing',True,original),('After backing',True,revised)]:
    if 'backing' in label:
        h,*t=re.split(r'(?m)(?=^  <TRACK )',text)
        text=h+''.join(t[:3])+'>\n'
    ext='wav' if wav else 'mp3'
    def media(m):
        name=m[1]
        src=next(d/name for d in (stage/'Media',project/'Media') if (d/name).is_file())
        return f'FILE "{src}"'
    text=re.sub(r'FILE "Media/([^"]+)"',media,text)
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
