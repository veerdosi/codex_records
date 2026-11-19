from faster_whisper import WhisperModel
import soundfile as sf, scipy.signal as ss, numpy as np, sys
from pathlib import Path
m=WhisperModel('small',download_root='work/shared/models',device='cpu',compute_type='int8',cpu_threads=3)
p=Path(sys.argv[1])
x,sr=sf.read(p,dtype='float32')
for s,e in zip(map(float,sys.argv[2::2]),map(float,sys.argv[3::2])):
 a=ss.resample_poly(x[int(s*sr):int(e*sr)].mean(1),160,441).astype('float32')
 seg,_=m.transcribe(a,language='hi',beam_size=1,temperature=0,max_new_tokens=120,word_timestamps=True,condition_on_previous_text=False,initial_prompt='लैला, मैं फ़रेबी।')
 for v in seg: print(round(v.start+s,2),round(v.end+s,2),v.text,[(round(w.start+s,2),round(w.end+s,2),w.word) for w in v.words or []],flush=True)
