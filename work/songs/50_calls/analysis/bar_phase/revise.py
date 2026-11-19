"""Restore the source bar phase of the second verse item on the 80 BPM grid."""
from pathlib import Path
import re, uuid
p=Path(__file__).resolve().parent
root=p.parents[4]
rpp=root/'reaper/50 Calls/50 Calls.rpp'
rpp=rpp.resolve()
x=rpp.read_text()
def newguid():return '{'+str(uuid.uuid4()).upper()+'}'
def change(item,field,value):
    return re.sub(rf'(?m)^(      {field} ).*$',lambda m:m[1]+str(value),item,count=1)
def split(m):
    a=m[0]
    if 'NAME "Kanye verse repaired.wav"' not in a: return a
    assert 'POSITION 30.25\n' in a and 'LENGTH 24.35\n' in a and 'SOFFS 0\n' in a
    # Split in the low-level gap after the first passage; leave every syllable intact.
    first=change(change(a,'LENGTH',11.99),'FADEOUT','1 0.028 0 1 0 0 0 1 0 0 1 0 0')
    second=change(change(change(a,'POSITION',43.74),'LENGTH',12.36),'SOFFS',11.99)
    second=change(second,'IID',145)
    second=change(change(second,'GUID',newguid()),'IGUID',newguid())
    second=change(second,'FADEIN','1 0.024 0 1 0 0 0 1 0 0 1 0 0')
    return first+second
x=re.sub(r'(?ms)^    <ITEM\n.*?^    >\n',split,x)
assert x.count('NAME "Kanye verse repaired.wav"')==2
# Keep the bed moving under the relocated last line. Ease it down across the following two beats.
for a,b in [(53.45,54.95),(54.0,55.50),(54.48,55.98),(53.42,54.92),(54.18,55.68),(53.82,55.32),(54.35,55.85)]:
    x=re.sub(rf'(?m)^(      PT ){a:g}( )',lambda m:f'{m[1]}{b:g}{m[2]}',x)
x=re.sub(r'(?m)^(  MARKER (?:4|5) )54 ',r'\g<1>55.5 ',x)
x=re.sub(r'(?m)^(  RENDER_FILE ).*$',r'\g<1>"50 Calls.mp3"',x)
(p/'50 Calls portable.rpp').write_text(x)
session=Path.home()/'Library/Application Support/REAPER/MCP Sessions/50 Calls Bar Phase'
session.mkdir(parents=True,exist_ok=True)
z=re.sub(r'(?m)^(\s+FILE ")Media/',lambda m:m[1]+str(rpp.parent/'Media')+'/',x)
z=re.sub(r'(?m)^(  RENDER_FILE ).*$',lambda m:m[1]+f'"{session}/50 Calls.mp3"',z)
(session/'50 Calls Bar Phase.rpp').write_text(z)
