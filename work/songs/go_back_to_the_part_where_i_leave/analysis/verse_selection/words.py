from pathlib import Path
import json
import subprocess
import sys
import numpy as np
from faster_whisper import WhisperModel
stage=Path(__file__).resolve().parent
r=stage.parents[1]
p=next((r.parents[1]/'shared/models/models--Systran--faster-whisper-base.en/snapshots').iterdir())
m=WhisperModel(str(p),device='cpu',compute_type='int8',cpu_threads=4)
for name, stop in zip(*[iter(sys.argv[1:])]*2):
    path=r/'sources'/f'{name}.wav'
    audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-t',stop,'-ar','16000','-ac','1','-f','f32le','-']),dtype=np.float32)
    result,_=m.transcribe(audio,language='en',word_timestamps=True,beam_size=3,condition_on_previous_text=False)
    rows=[{'start':s.start,'end':s.end,'text':s.text.strip(),'words':[[w.start,w.end,w.word] for w in s.words]} for s in result]
    (stage/f'{name}_words.json').write_text(json.dumps(rows))
    for s in rows: print(name,round(s['start'],2),round(s['end'],2),s['text'],flush=True)
