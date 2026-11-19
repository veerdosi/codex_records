"""Build piano-free v1 and a separate v3 with new synth phrases."""
from pathlib import Path
import json
import re
from uuid import uuid4

stage=Path(__file__).resolve().parent
root=stage.parents[4]
base=root/'reaper/Muh Pe Lovey Dovey v1'
project_file=base/(base.name+'.rpp')
inputs=stage/'Source v1.rpp'
if not inputs.exists():
    inputs.write_text(project_file.read_text())
original=inputs.read_text()
def field(text,key,value,indent):
    return re.sub(rf'(?m)^{indent}{key} .*$',f'{indent}{key} {value}',text)

def timing(text,end):
    text=re.sub(r'(?m)^  RENDER_RANGE 0 0 \S+',f'  RENDER_RANGE 0 0 {end:.12f}',text)
    return re.sub(r'(?m)^  MARKER 11 \S+ "" 1$',f'  MARKER 11 {end:.12f} "" 1',text)

def guid():
    return '{'+str(uuid4()).upper()+'}'

all_clips=json.loads((stage/'clips.json').read_text())
for version,end in [(1,206.11764705882354),(2,213.4076671123),(3,207.370588235294)]:
    base_path=root/f'reaper/Muh Pe Lovey Dovey v{2 if version==2 else 1}'
    if version==2:
        source_path=stage/'Source v2.rpp'
        if not source_path.exists():
            source_path.write_text((base_path/(base_path.name+'.rpp')).read_text())
        baseline=source_path.read_text()
    else:
        baseline=original
    tracks=re.split(r'(?m)(?=^  <TRACK )',baseline)
    synth=tracks.pop().rstrip().removesuffix('>').rstrip()+'\n'
    assert 'NAME "Veer | Upright piano and stereo echo"' in synth
    revised=synth.replace('Upright piano and stereo echo','Synth cues and stereo echo')
    if version!=1:
        piano_items=list(re.finditer(r'(?ms)^    <ITEM\n.*?^    >$',synth))
        clips=all_clips[3:] if version==2 else all_clips[:3]
        assert len(piano_items)==len(clips)==3
        for item,(name,pos,length) in zip(piano_items,clips):
            new=item[0]
            old_name=re.search(r'FILE "Media/(.*?)"',new)[1]
            for key,value in dict(POSITION=pos,LENGTH=length,IGUID=guid(),GUID=guid()).items():
                new=field(new,key,value,'      ')
            revised=revised.replace(item[0],new.replace(old_name,name))
        if version==2:
            # The cue itself has its own two pan positions before the
            # ramp. The ramp's pan gesture still belongs to the backing.
            revised=re.sub(r'(?ms)^    <PANENV2\n.*?^    >\n','',revised)
    text=''.join(tracks)+(revised if version!=1 else '')+'>\n'
    if version==3:
        text=text.replace('Muh Pe Lovey Dovey v1','Muh Pe Lovey Dovey v3')
    text=timing(text,end)
    (stage/f'Portable v{version}.rpp').write_text(text)
    def absolute(m):
        name=m[1]
        source=next(p for d in (stage/'Media',base_path/'Media') if (p:=d/name).is_file())
        return f'FILE "{source}"'
    for label in ('Premaster','Master'):
        ext='wav' if label=='Premaster' else 'mp3'
        draft=re.sub(r'FILE "Media/([^"]+)"',absolute,text)
        draft=field(draft,'RENDER_FILE',f'"{stage/f"v{version} {label}.{ext}"}"','  ')
        if label=='Premaster':
            draft=field(draft,'RENDER_NORMALIZE','0 0 0 0 0 0 0','  ')
            draft=field(draft,'RENDER_STEMS','0','  ')
            draft=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',draft)
        (stage/f'v{version} {label}.rpp').write_text(draft)
