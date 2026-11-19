from pathlib import Path
import re
import sys

stage=Path(__file__).resolve().parent
root=stage.parents[4]
version=int(sys.argv[1])
title=f'Muh Pe Lovey Dovey v{version}'
project=root/'reaper'/title
parts=re.split(r'(?m)(?=^  <TRACK )',(project/(title+'.rpp')).read_text())
parts[-1]=parts[-1].rstrip().removesuffix('>').rstrip()+'\n'
media=project/'Media'
for name, track_no in [('Drums',1),('Bass',2),('Harmony',3),('Piano',10)]:
    out=parts[0]+parts[track_no]+'>\n'
    # Analyze the source stems before the headphone pan and level rides.
    out=re.sub(r'(?ms)^    <PANENV2\n.*?^    >\n','',out)
    out=re.sub(r'FILE "Media/([^"]+)"',lambda m:f'FILE "{media/m[1]}"',out)
    out=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{stage/f"v{version} {name}.wav"}"',out)
    out=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',out)
    out=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',out)
    out=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',out)
    # Keep time relative to the source session by rendering from zero.
    (stage/f'v{version} {name}.rpp').write_text(out)
