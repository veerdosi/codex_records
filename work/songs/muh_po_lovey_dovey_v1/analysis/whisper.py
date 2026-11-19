import json,sys
import numpy as np,subprocess
from pathlib import Path
from faster_whisper import WhisperModel
m=WhisperModel('small',download_root='work/shared/models',device='cpu',compute_type='int8',cpu_threads=4)
for arg in sys.argv[1:]:
 p=Path(arg)
 s, i=m.transcribe(np.frombuffer(subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(p),'-ac','1','-ar','16000','-f','f32le','-']),dtype='<f4'),language='hi',word_timestamps=True,beam_size=3,condition_on_previous_text=False)
 out=[{'start':round(x.start,2),'end':round(x.end,2),'text':x.text,'words':[(w.start,w.end,w.word,w.probability) for w in x.words or []]} for x in s]
 dest=Path(__file__).parent/(p.parent.name+'_'+p.stem+'_words.json')
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2))
