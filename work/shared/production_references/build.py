"""Extract the marked references and assemble a level-matched REAPER session."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parent


def output(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def source_audio(cache, name, url):
    extensions = ('.webm', '.m4a', '.opus', '.mp3', '.wav')
    for ext in extensions:
        path = cache / (name + ext)
        if path.is_file():
            return path
    subprocess.run(['yt-dlp', '--no-playlist', '--no-progress', '-f',
                    'bestaudio[ext=webm]/bestaudio', '-o', str(cache / (name + '.%(ext)s')), url],
                   check=True)
    return next(path for path in cache.glob(f'{name}.*') if path.suffix in extensions)


def extract(row):
    clip, source = row
    start, end = clip['start_seconds'], clip['end_seconds']
    path = ROOT / clip['file']
    path.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(source),
                    '-t',str(end-start),'-map','0:a:0','-ar','44100','-ac','2',
                    '-map_metadata','-1','-c:a','flac','-sample_fmt','s32',
                    '-bits_per_raw_sample','24',str(path)],check=True)
    probe=json.loads(output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    stream=probe['streams'][0]
    duration=float(probe['format']['duration'])
    if abs(duration-(end-start))>.035 or stream['channels']!=2 or stream['codec_name']!='flac':
        raise ValueError(f'Unexpected clip length or format for {path.name}')
    report=output(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',
                   'loudnorm=I=-18:TP=-1:LRA=11:print_format=json','-f','null','-'])
    meter=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',report,re.S)[0])
    loudness,peak=map(float,(meter['input_i'],meter['input_tp']))
    gain=min(-18-loudness,-1-peak,8)
    return {'duration_seconds':duration,'integrated_lufs':loudness,
            'true_peak_dbtp':peak,'audition_gain_db':round(gain,2)}


def ident(key):
    return '{'+str(uuid5(NAMESPACE_URL,'local-music-reference/'+key)).upper()+'}'


def safe_label(label):
    return label.replace('"',"'").replace('\n',' ')


def create_project(cases, measurements):
    categories={'handoff':'Vocal handoffs and DJ transitions',
                'sample composition':'Composing from samples',
                'genre change':'New genres and backing'}
    tracks={kind:[] for kind in categories}
    markers=[]
    position=0.
    index=0
    for case in cases:
        for clip in case['clips']:
            index+=1
            data=measurements[clip['file']]
            title=safe_label(f'{case["title"]} [{clip["role"]}]')
            markers.append((position,title))
            if 'cue_seconds' in clip and clip['cue_seconds']>clip['start_seconds']:
                cue=position+clip['cue_seconds']-clip['start_seconds']
                markers.append((cue,clip['cue_label']))
            gain=10**(data['audition_gain_db']/20)
            tracks[case['kind']].append(f'''    <ITEM
      POSITION {position:.9f}
      LENGTH {data['duration_seconds']:.9f}
      LOOP 0
      FADEIN 1 0.005 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.005 0 1 0 0 0 1 0 0 1 0 0
      NAME "{title}"
      VOLPAN {gain:.10f} 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      IID {index}
      IGUID {ident(clip['file']+'/item')}
      GUID {ident(clip['file']+'/take')}
      <SOURCE FLAC
        FILE "{clip['file']}"
      >
    >
''')
            data['session_start_seconds']=round(position,6)
            position+=data['duration_seconds']+1.2
        position+=.8
    header='''<REAPER_PROJECT 0.1 "7.85/macOS-arm64" 0 0
  TITLE "Production References"
  SAMPLERATE 44100 1 0
  TEMPO 120 4 4 0
  TIMELOCKMODE 0
  TIMEMODE 1 5 -1 30 0 0 -1 0
  MASTER_VOLUME 1 0 -1 -1 1
'''
    for i,(at,title) in enumerate(markers,1):
        header+=f'  MARKER {i} {at:.9f} "{safe_label(title)}" 0 0 1 B {ident(str(i))} 0 1\n'
    for kind,name in categories.items():
        header+=f'''  <TRACK {ident(kind)}
    NAME "{name}"
    VOLPAN 1 0 -1 -1 1
    MAINSEND 1 0
    NCHAN 2
'''+''.join(tracks[kind])+'  >\n'
    (ROOT/'Production References.rpp').write_text(header+'>\n')


def build(cache):
    data=json.loads((ROOT/'manifest.json').read_text())
    sources={name:source_audio(cache,name,value['url']) for name,value in data['sources'].items()}
    clips=[clip for case in data['cases'] for clip in case['clips']]
    for clip in clips:
        duration=data['sources'][clip['source']]['duration_seconds']
        assert 0<=clip['start_seconds']<clip['end_seconds']<=duration
        if 'cue_seconds' in clip:
            assert clip['start_seconds']<=clip['cue_seconds']<clip['end_seconds']
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=pool.map(extract,[(clip,sources[clip['source']]) for clip in clips])
        measurements={clip['file']:result for clip,result in zip(clips,rows)}
    create_project(data['cases'],measurements)
    (ROOT/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
    print(f'Built {len(clips)} excerpts from {len(sources)} uploads.')


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,help='Optional directory of previously downloaded source audio')
    args=parser.parse_args()
    if args.cache:
        build(args.cache)
    else:
        with TemporaryDirectory(prefix='production-references-') as tmp:
            build(Path(tmp))
