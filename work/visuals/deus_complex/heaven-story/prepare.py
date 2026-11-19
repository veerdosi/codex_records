"""Prepare stadium plates, deterministic grain and beat cues for the Story."""
from pathlib import Path
import json
import subprocess

import numpy as np
from PIL import Image
from scipy import signal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PUBLIC = HERE/'public'
SOURCE = ROOT/'outputs/deus complex/audio/this_must_be_heaven.mp3'
START = 25.57142857142857
DURATION = 59
RATE = 22050

picture=Image.open(HERE.parent/'stage_source.png').convert('RGB')
# Trim the screenshot border and carousel controls while preserving the performer.
picture=picture.crop((62,8,813,1120))
picture.save(PUBLIC/'stadium.jpg',quality=96)

for seed in range(12):
 rng=np.random.default_rng(seed+172)
 gray=np.clip(rng.normal(127,34,(384,216)),0,255).astype('uint8')
 Image.fromarray(gray).save(PUBLIC/'grain'/f'{seed:02}.png')

subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-ss',str(START),'-i',str(SOURCE),
                '-t',str(DURATION),'-af','afade=t=in:d=0.035,afade=t=out:st=58.4:d=0.6',
                '-ac','2','-ar','48000','-c:a','pcm_s24le',str(PUBLIC/'music.wav')],check=True)

raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(SOURCE),'-ac','1','-ar',str(RATE),'-f','f32le','pipe:1'])
x=np.frombuffer(raw,dtype='<f4').copy()
band=signal.sosfilt(signal.butter(3,[40,155],btype='bandpass',fs=RATE,output='sos'),x)
frame=int(RATE*.01)
power=np.sqrt(np.mean(band[:len(band)//frame*frame].reshape(-1,frame)**2,axis=1))
envelope=power/max(1e-6,np.percentile(power,95))
fps=30
frame_times=START+np.arange(round(DURATION*fps))/fps
pulse=np.interp(frame_times,np.arange(len(power))*.01,envelope)
metadata={'sourceStartSeconds':START,'durationSeconds':DURATION,'bpm':105,'fps':fps,
 'cutsSeconds':[0,1.857142857,6.428571429,11,15.571428571,20.142857143,24.714285714,
                29.285714286,33.857142857,38.428571429,40.714285714,45.285714286,49.857142857,
                54.428571429,59],
 'hookReturnSeconds':66.28571428571428-START,
 'pulse':np.round(pulse,4).tolist()}
(PUBLIC/'timing.json').write_text(json.dumps(metadata))
print(json.dumps({k:v for k,v in metadata.items() if k!='pulse'},indent=2))
