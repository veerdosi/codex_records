from pathlib import Path
import json, re, shutil, subprocess, sys
title='Muh Pe Lovey Dovey'
slug='muh_pe_lovey_dovey'
root=Path.cwd()
session=Path.home()/'Library/Application Support/REAPER/MCP Sessions'/title
rpp=session/(title+'.rpp')
project=root/'reaper'/title
source=session/'Renders'/(title+'.mp3')
cfg=json.loads((Path(__file__).parent/'arrangement.json').read_text())
def clone(src,dst):
    if dst.exists() and dst.stat().st_size==src.stat().st_size:
        return
    if subprocess.run(['cp','-c',str(src),str(dst)],capture_output=True).returncode:
        shutil.copy2(src,dst)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
  'format=duration,bit_rate:format_tags=artist,album,title:stream=codec_name,channels,sample_rate',
  '-of','json',str(source)]))
assert abs(float(probe['format']['duration'])-cfg['duration'])<.05, probe
assert probe['format']['tags']=={'title':title,'artist':cfg['artist'],'album':'unfinished'}, probe
assert probe['streams'][0]['codec_name']=='mp3' and probe['streams'][0]['channels']==2
x=rpp.read_text()
real=[]
for i,track in enumerate(re.split(r'^  <TRACK ',x,flags=re.M)[1:]):
    for item in re.findall(r'^    <ITEM\n(.*?)^    >',track,flags=re.M|re.S):
        def number(field):
            return float(re.search(fr'^\s+{field} ([\d.eE+-]+)',item,re.M)[1])
        file=Path(re.search(r'^\s+FILE "([^"]+)"',item,re.M)[1]).name
        real.append([i,file,number('SOFFS'),number('LENGTH'),number('POSITION')])
def key(a):return tuple(a[:2])+tuple(round(n,5) for n in a[2:5])
assert sorted(map(key,cfg['items']))==sorted(map(key,real)), 'REAPER item edges differ from the planned cuts'
(project/'Media').mkdir(parents=True,exist_ok=True)
for f in set(re.findall(r'^\s+FILE "([^"]+)"',x,re.M)):
    old=Path(f)
    assert old.parent==session/'Media' and old.is_file(),old
    clone(old,project/'Media'/old.name)
    x=x.replace('FILE "'+f+'"','FILE "Media/'+old.name+'"')
x=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "Renders/{title}.mp3"',x)
(project/(title+'.rpp')).write_text(x)
print('Verified REAPER clips:',len(real),'Portable media:',len(set(t[1] for t in real)))
print(json.dumps(probe['format'],indent=2))
if '--deliver' in sys.argv:
    dest=root/'outputs/unfinished'/(slug+'.mp3')
    temp=dest.with_suffix('.staging')
    shutil.copy2(source,temp)
    temp.replace(dest)
    print('Final:',dest)
