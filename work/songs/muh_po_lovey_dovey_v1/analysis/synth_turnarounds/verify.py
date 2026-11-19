"""Verify the localized edits, channel order and pre-ramp clearance."""
from pathlib import Path
import json
import re
import subprocess

import numpy as np
import soundfile as sf

stage=Path(__file__).resolve().parent
sr=48000
frames=lambda t: round(t*sr)

def check_delta(a,b,allowed):
    end=min(len(a),len(b))
    delta=np.abs(a[:end]-b[:end])
    gaps=zip([0]+[frames(t[1])+2 for t in allowed],
             [frames(t[0])-2 for t in allowed]+[end])
    for start,stop in gaps:
        if start >= min(stop,end):
            continue
        assert np.max(delta[start:stop])<2.5e-7, (start,stop)
    return delta

clip_info=json.loads((stage/'clips.json').read_text())
previous=stage.parent/'even_tempo'
old_v1,_=sf.read(previous/'fixed/Premaster.wav',dtype='float32')
old_v2,_=sf.read(previous/'native/Premaster.wav',dtype='float32')
new=[]
for version,starts,expected in [(1,[88.17035,166.89882],206.117647),
                                (2,[89.19393,171.80254],213.407667),
                                (3,[88.17035,166.89882],207.370588)]:
    y,rate=sf.read(stage/f'v{version} Premaster.wav',dtype='float32')
    assert rate==sr and abs(len(y)/sr-expected)<1/sr, (version,len(y)/sr)
    assert np.isfinite(y).all()
    master=stage/f'v{version} Master.mp3'
    assert master.stat().st_size>=int((expected-.1)*39900)
    data=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-xerror',
        '-i',str(master),'-f','f32le','-'])
    decoded=np.frombuffer(data,'<f4').reshape(-1,2)
    assert abs(len(decoded)-len(y))<=2
    for t in starts:
        left=decoded[frames(t+.18):frames(t+.58)]
        right=decoded[frames(t+.88):frames(t+1.26)]
        level=lambda x:10*np.log10(np.mean(x*x,axis=0)+1e-12)
        l,r=level(left),level(right)
        assert l[0]-l[1]>25 and r[1]-r[0]>25
    assert np.max(np.abs(y[-frames(.001):]))<.0001
    new.append(y)
for ver,a,b,span in [
    (1,old_v1,new[0],[(88.235294,91.716),(166.941176,170.422),(201.882352,210.352942)]),
    (2,old_v2,new[1],[(88.827,92.742),(171.435,175.283),(206.74289,216.28835)]),
    (3,new[0],new[2],[(t,t+d) for _,t,d in clip_info[:3]]),
]:
    check_delta(a,b,span)
    print(f'v{ver}: edit scope and rendered stereo verified')
for (name,t,span), ramp, voice_end in zip(clip_info[3:5],
        [89.193932437720,171.802540106952],[88.825151949915,170.990466936220]):
    assert t>voice_end and abs(ramp-t-span-.026)<1e-9
    print(name,'ends',round(t+span,4),'before ramp',round(ramp,4))
