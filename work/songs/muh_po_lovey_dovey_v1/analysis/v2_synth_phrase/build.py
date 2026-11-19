"""Compose a one-beat Farebi turnaround pickup for v2."""
from pathlib import Path
import re
import subprocess

import pretty_midi

stage=Path(__file__).resolve().parent
root=stage.parents[4]
title='Muh Pe Lovey Dovey v2'
project=root/'reaper'/title
source=stage/'Before.rpp'
if not source.exists():
    source.write_text((project/(title+'.rpp')).read_text())
original=source.read_text()
revised=original
beat=60/82
duration=beat-.029
# Dry struck synth with a short filtered resonator. The restrained
# opening hits pick up the outgoing groove, then the upper notes answer
# after Encore's vocal tail and land on E before the ramp starts.
orchestra='''<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=16
nchnls=2
0dbfs=1
instr 1
  iHz = cpsmidinn(p4)
  aEnv linseg 0,.004,1,.017,.68,p3-.021,0
  kBrightness expon 1.5,p3,.13
  aCore foscil .73*aEnv*p5,iHz,1,2,kBrightness,1
  aOct oscili .12*aEnv*p5,iHz*2,1
  aSoft tone aCore+aOct,4650
  outs aSoft*sqrt(1-p6),aSoft*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
'''
parts=[
 ('Encore',89.193932437720,[
     (.080,.153,59,.205,.43),(.083,.135,64,.115,.52),
     (.329,.151,71,.265,.54),
     (.501,.183,76,.350,.47),(.504,.172,71,.164,.52),
 ]),
 ('Calm',171.802540106952,[
     (.103,.140,59,.211,.43),(.109,.125,64,.115,.52),
     (.332,.143,71,.265,.56),
     (.514,.172,76,.350,.48),(.518,.166,71,.164,.51),
 ]),
]
items=re.compile(r'(?ms)^    <ITEM\n.*?^    >$')
for rapper,ramp,notes in parts:
    start=ramp-beat
    assert max(t+d for t,d,*_ in notes)<duration
    name=f'Veer - {rapper} turnaround phrase'
    path=stage/'Media'/name
    pattern=re.compile(rf'(?m)^      POSITION (\S+)')
    hits=[m for m in items.finditer(revised) if f'FILE "Media/Veer - {rapper} synth pickup.wav"' in m[0]]
    assert len(hits)==1
    old=hits[0][0]
    cue=old.replace(f'Veer - {rapper} synth pickup.wav',name+'.wav')
    cue=pattern.sub(f'      POSITION {start:.12f}',cue)
    cue=re.sub(r'(?m)^      LENGTH \S+',f'      LENGTH {duration:.12f}',cue)
    cue=cue.replace('FADEOUT 1 0.045 ','FADEOUT 1 0.012 ')
    revised=revised.replace(old,cue)
    events=''.join(f'i 1 {t:.6f} {d:.6f} {n} {gain:.6f} {pan:.4f}\n'
                   for t,d,n,gain,pan in notes)
    csd=path.with_suffix('.csd')
    csd.write_text(orchestra+events+f'f 0 {duration:.12f}\ne\n</CsScore>\n')
    subprocess.run(['csound','-o',str(path.with_suffix('.wav')),str(csd)],check=True)
    midi=pretty_midi.PrettyMIDI(initial_tempo=82,resolution=960)
    inst=pretty_midi.Instrument(81,name='Veer struck synth')
    inst.notes=[pretty_midi.Note(round(g*184+26),n,t,t+d) for t,d,n,g,_ in notes]
    midi.instruments.append(inst)
    midi.write(str(path.with_suffix('.mid')))

(stage/'Portable.rpp').write_text(revised)
for label,ext in [('Premaster','wav'),('Master','mp3')]:
    def resolve(m):
        path=next(d/m[2] for d in (stage/'Media',project/'Media') if (d/m[2]).is_file())
        return f'{m[1]}"{path}"'
    text=re.sub(r'(?m)^([ \t]*FILE )"Media/([^"]+)"',resolve,revised)
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if ext=='wav':
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)
