from pathlib import Path
import json, re, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

p = Path(__file__).resolve().parents[5]
title = 'Go Back to the Part Where I Leave'
project = p/'reaper'/title
analysis = Path(__file__).resolve().parent
rate = 44100
rpp = (Path(sys.argv[1]) if len(sys.argv)>1 else project/f'{title}.rpp').read_text()
pattern = r'^\s+{} (\S+)'
def val(item, key):
    return float(re.search(pattern.format(key),item,re.M)[1])
def grab(track, lo, hi):
    result = np.zeros((round(hi*rate)-round(lo*rate),2), np.float32)
    for item in re.split(r'(?m)^    <ITEM\b',track)[1:]:
        pos, length, offset = (round(val(item,key)*rate) for key in ['POSITION','LENGTH','SOFFS'])
        start, end = max(pos,round(lo*rate)),min(pos+length,round(hi*rate))
        if end<=start: continue
        path = Path(re.search(r'(?m)^        FILE "([^"]+)"',item)[1])
        if not path.is_absolute(): path=project/path
        with sf.SoundFile(path) as f:
            f.seek(start-pos+offset)
            x=f.read(end-start,dtype='float32',always_2d=True)
        result[start-round(lo*rate):start-round(lo*rate)+len(x)] += x
    return result
model_path=next((p/'work/shared/models/models--Systran--faster-whisper-base.en/snapshots').iterdir())
model=WhisperModel(str(model_path),device='cpu',compute_type='int8',cpu_threads=4)
tests=[('Kanye West',56,69),('Runaway | Instrumental',60,67),('21 Savage',64,70),('21 Savage',88,97),('Kanye West',93,99),('Eminem |',97,104),('Eminem |',124,132),('Kanye West',131,140)]
for name,lo,hi in tests:
    track=next(t for t in re.split(r'(?m)^  <TRACK ',rpp)[1:] if re.search(r'^    NAME "([^"]+)"',t,re.M)[1].startswith(name))
    x=grab(track,lo,hi)
    if np.max(np.abs(x))<1e-4:
        print(name,lo,'silent',flush=True);continue
    y=resample_poly(x.mean(axis=1),160,441)
    seg,_=model.transcribe(y,language='en',word_timestamps=True,beam_size=4,condition_on_previous_text=False,no_speech_threshold=.5)
    rows=[(round(w.start+lo,2),round(w.end+lo,2),w.word,round(w.probability,2)) for s in seg for w in s.words]
    print(name,lo,json.dumps(rows),flush=True)
