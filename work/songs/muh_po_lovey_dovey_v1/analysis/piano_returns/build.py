"""Stage the constant-tempo mix and rebuild the four equal tempo ramps."""
from pathlib import Path
import json
import re
import sys
from uuid import uuid4
from extend import extend

here=Path(__file__).resolve().parent
root=here.parents[4]
variant=sys.argv[1]
native=variant=='native'
stage=here/variant
title=f'Muh Pe Lovey Dovey v{2 if native else 1}'
sources=here.parents[1]/'previous_exports/Before stereo turnarounds'
old_project=sources/'Muh Po Lovey Dovey v1'
fixed_project=sources/'Muh Pe Lovey Dovey v3'
existing=(here.parent/'source_tempo/build.py').read_text()
prep=existing[:existing.index("original = (project")]
prep=prep.replace("stage = Path(__file__).resolve().parent","stage = Path(__file__).resolve().parent/'+VARIANT'")
prep=prep.replace("'+VARIANT'",repr(variant))
prep=prep.replace('root = stage.parents[4]', 'root = stage.parents[5]')
prep=prep[:prep.index('sources = ')] + "stems = ('drums','bass','music','chorus')\n"
dsp=existing[existing.index('def field('):existing.index("tempo=(stage")]
dsp=dsp.replace("if start+1e-7<t<end-1e-7", "if start+1e-7<t<end-1e-7 and (not definitions[bars.index(t)-1][2] or not definitions[bars.index(t)][2])")
dsp=dsp.replace("np.arange(left,right,.125),right","np.arange(left,right,.125),[b for b in bars if left<b<right],right")
# A repeated source bar can be in the middle of one ramp. Warp its
# pieces against the same timeline, with a unique staged filename.
env={'__file__':__file__}
exec(compile(prep+dsp, str(here.parent/'source_tempo/build.py'),'exec'),env)

at=env['at']
env['media']=old_project/'Media'
if native:
    text=extend((old_project/(old_project.name+'.rpp')).read_text())
    previous_map=re.search(r'(?ms)^  <TEMPOENVEX\n.*?^  >$',text)[0]
    new_map=re.search(r'(?ms)^  <TEMPOENVEX\n.*?^  >$',(stage/'Tempo map.rpp').read_text())[0]
    for i,(t,bpm) in enumerate(re.findall(r'^    PT (\S+) (\S+)',new_map,re.M)):
        assert abs(float(t)-env['points'][i])<1e-8 and float(bpm)==env['definitions'][i][1]
    text=re.sub(r'^    <ITEM\n.*?^    >$',env['move_item'],text,flags=re.M|re.S)
    text=text.replace(previous_map,new_map)
    text=re.sub(r'^  TEMPO 80\b','  TEMPO 90',text,flags=re.M)
    text=re.sub(r'(?m)^(  MARKER \d+ |      PT )([\d.]+)',
                 lambda m:m[1]+f'{at(float(m[2])):.12f}',text)
    old_end=at(225)
else:
    text=(fixed_project/(fixed_project.name+'.rpp')).read_text()
    old_end=at(219)
    text=re.sub(r'(?m)^    <ITEM\n(?:(?!^    >$)[\s\S])*?FILE "Media/Veer - pickup keys\.wav"(?:(?!^    >$)[\s\S])*?^    >\n','',text)
end=at(229.5 if native else 223.5)
text=re.sub(r'Muh P[oe] Lovey Dovey v[123]',title,text)
text=re.sub(r'(?m)^  RENDER_RANGE 0 0 \S+',f'  RENDER_RANGE 0 0 {end:.12f}',text)
text=re.sub(r'(?m)^  MARKER 11 [\d.]+ "" 1$',f'  MARKER 11 {end:.12f} "" 1',text)

def guid():
    return '{'+str(uuid4()).upper()+'}'
def piano_item(name,pos,duration):
    return f"""    <ITEM
      POSITION {pos:.12f}
      LENGTH {duration:.12f}
      LOOP 0
      FADEIN 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.045 0 1 0 0 0 1 0 0 1 0 0
      IGUID {guid()}
      NAME "{name}"
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      GUID {guid()}
      <SOURCE WAVE
        FILE "Media/{name}"
      >
    >
"""

# Pan the breakdown as a single arrangement gesture. Each stage has
# a quiet transition in level around the switch, then the hook opens up.
pans=[]
for beat_start in ((93.681,180.777375) if native else (93.681,177.33)):
    t=lambda beats:at(beat_start+beats*.75)
    pans += [(t(-.10),0),(t(0),-1),(t(1.81),-1),
             (t(1.98),1),(t(3.80),1),(t(4.02),0)]
def pan_envelope():
    points=''.join(f'      PT {t:.12f} {-p} 0\n' for t,p in [(0.,0),*pans])
    return ('    <PANENV2\n'+f'      EGUID {guid()}\n'
           '      ACT 1 -1\n      VIS 1 1 1\n      LANEHEIGHT 0 0\n'
           '      ARM 0\n      DEFSHAPE 0 -1 -1\n'+points+'    >\n')

header,*tracks=re.split(r'(?m)(?=^  <TRACK )',text)
tracks[-1]=tracks[-1].rstrip().removesuffix('>').rstrip()+'\n'
for i,track in enumerate(tracks):
    # Vocals stay on their own tracks, with the entrance unpanned.
    if i in (0,1,2,6,7,8):
        tracks[i]=track.replace('    <ITEM\n', pan_envelope()+'    <ITEM\n',1)
    if i in (0,1):
        env=re.search(r'(?ms)^    <VOLENV3\n.*?^    >$',tracks[i])[0]
        original_points=[(float(a),float(b)) for a,b in re.findall(
            r'(?m)^      PT (\S+) (\S+) 0$',env)]
        def original_volume(t):
            for (a,v),(b,w) in zip(original_points,original_points[1:]):
                if a <= t <= b:
                    return v+(w-v)*(t-a)/(b-a)
            return original_points[-1][1]
        rides=[]
        for beat_start in ((93.681,180.777375) if native else (93.681,177.33)):
            t=lambda beats:at(beat_start+beats*.75)
            for beat,db in [(-.25,0),(0,-1),(1.75,-3.4),(2,-4),(2.40,-2.6),(3.80,-1.8),(4.12,0)]:
                time=t(beat)
                rides.append((time,original_volume(time)*10**(db/20)))
        both=sorted(original_points+rides)
        new_env=re.sub(r'(?m)^      PT .*\n','',env).removesuffix('    >')
        new_env+=''.join(f'      PT {t:.12f} {v:.12f} 0\n' for t,v in both)+'    >'
        tracks[i]=tracks[i].replace(env,new_env)

track_id=guid()
piano=json.loads((stage/'piano.json').read_text())
keys=(f'  <TRACK {track_id}\n    NAME "Veer | Upright piano and stereo echo"\n'
      '    BEAT 0\n    VOLPAN 1 0 -1 -1 1\n    PANLAWFLAGS 3\n    PANMODE 3\n'
      f'    TRACKID {track_id}\n    NCHAN 2\n    MAINSEND 1 0\n'+pan_envelope()+
      ''.join(piano_item(*item) for item in piano)+'  >\n')
text=header+''.join(tracks)+keys+'>\n'
(stage/'Portable.rpp').write_text(text)
def resolve(m):
    for directory in (stage/'Media',old_project/'Media',fixed_project/'Media'):
        path=directory/m[1]
        if path.is_file():
            return f'FILE "{path}"'
    raise FileNotFoundError(m[1])
for label,ext in [('Premaster','wav'),('Master','mp3')]:
    out=re.sub(r'FILE "Media/([^"]+)"',resolve,text)
    out=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/label}.{ext}"',out)
    if ext=='wav':
        out=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',out)
        out=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',out)
        out=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',out)
    (stage/f'{label}.rpp').write_text(out)
print(variant,'outro original end',old_end,'revised end',end,'pan points',pans)
