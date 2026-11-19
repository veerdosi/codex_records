from pathlib import Path
import sys,json,math
import soundfile as sf
from scipy.signal import resample_poly
from faster_whisper import WhisperModel
p=Path(__file__).resolve().parent
m=WhisperModel(str(next((Path(__file__).resolve().parents[3] / 'shared/models/models--Systran--faster-whisper-base.en/snapshots').iterdir())),device='cpu',compute_type='int8',cpu_threads=4)
for name in sys.argv[1:]:
    x,s=sf.read(p/f'{name}.wav',dtype='float32',always_2d=True)
    g=math.gcd(s,16000); x=resample_poly(x.mean(1),16000//g,s//g)
    seg,_=m.transcribe(x,language='en',beam_size=4,word_timestamps=True,condition_on_previous_text=False)
    rows=[]
    for a in seg:
        rows.append(dict(start=a.start,end=a.end,text=a.text,words=[(w.word,w.start,w.end) for w in a.words or []]))
        print(name,round(a.start,2),round(a.end,2),a.text.strip(),flush=True)
    (p/f'{name}_words.json').write_text(json.dumps(rows))
