from pathlib import Path
import json
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
from pedalboard import Compressor, PeakFilter, Reverb
from scipy import ndimage, signal
import soundfile as sf

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from dsp import SR, db, fade, filt, load

BEAT = 60/138
BAR = 4*BEAT
GRID = .03655
ACAPELLA_OFFSET = .02262

def sample(t):
    return round(t*SR)

def take(x,start,end):
    return x[sample(start):sample(end)].copy()

def power(x):
    return float(np.mean(x*x)+1e-12)

def body(x):
    return np.sqrt(power(filt(x,'bandpass',(600,4100))))

def put(bus,x,at):
    i=sample(at)
    assert 0<=i and i+len(x)<=len(bus)
    bus[i:i+len(x)] += x

def room(x,size=.30):
    padded=np.pad(x,((0,sample(.65)),(0,0)))
    effect=Reverb(room_size=size,damping=.76,dry_level=0,wet_level=1,width=.93)
    return filt(filt(effect(padded.T.copy(),SR).T,'highpass',430),'lowpass',5600)

beat=load(P/'beat.wav')
bed=beat*db(-4.05)
# Open on Yeat's synth. Bring the low end forward over the fourth bar.
intro_end=GRID+4*BAR
intro=slice(0,sample(intro_end))
intro_time=np.arange(intro.stop)/SR
intro_shape=1-np.sin(np.pi/2*np.clip((intro_time-intro_end+BAR)/BAR,0,1))**2
low=signal.butter(2,145,btype='lowpass',fs=SR,output='sos')
bass=signal.sosfiltfilt(low,bed[:sample(intro_end+.25)],axis=0)[intro]
bed[intro]-=(bass*(1-db(-5.5))*intro_shape[:,None]).astype(np.float32)
# Let the last hit decay to silence within the original duration.
tail=sample(.15)
bed[-tail:]*=np.cos(np.linspace(0,np.pi/2,tail,dtype=np.float32))[:,None]**2

voice=np.zeros_like(bed)
fx=np.zeros_like(bed)
source=load(P/'offgrid_studio.wav')
events=[]

def vocal(name, source_at, source_end, origin, bar, goal, *, release=.11):
    dry=take(source,source_at+ACAPELLA_OFFSET,source_end+ACAPELLA_OFFSET)
    dry=filt(dry,'highpass',86)
    dry=PeakFilter(cutoff_frequency_hz=2440,gain_db=.35,q=.8)(dry.T.copy(),SR).T
    dry=Compressor(threshold_db=-24.0,ratio=1.8,attack_ms=13,release_ms=87)(dry.T.copy(),SR).T
    dry=fade(dry,.016,release)
    at=GRID+bar*BAR+source_at-origin
    stop=at+len(dry)/SR
    target=take(bed,at+.10,stop-.04)
    # Measure only occupied windows so rests retain their shape.
    hop=sample(.06)
    n=len(dry)//hop
    q=filt(dry,'bandpass',(600,4100))[:n*hop].reshape(n,hop,2)
    r=np.mean(q*q,axis=(1,2))
    active=r>np.percentile(r,75)*.22
    occupied=np.sqrt(float(r[active].mean()))
    dry*=db(goal)*body(target)/max(occupied,1e-7)
    put(voice,dry,at)
    put(fx,room(dry)*.055,at)
    events.append(dict(name=name,at=at,stop=stop,source_bounds=[source_at,source_end],
                       native_grid=origin,native_bpm=138,target_bar=bar))

# One extended chorus, one verse, then the chorus returns after the drum break.
vocal('chorus 1 / refrain',308.64,321.11,308.84,4,2.7)
vocal('chorus 1 / extension',308.64,328.13,308.84,12,2.8)

# Keep the natural delivery and place the two long passages on the original bar grid.
# The line crossing the flute entry leaves a short breath before the next pickup.
vocal('verse / build',244.18,272.74,223.62+13*BAR,25,2.8,release=.07)
vocal('verse / flute response',273.48,295.27,272.31,39.75,2.65,release=.045)
# Finish the thought through the drum dropout, as the reference verse does.
vocal('verse / drum break',297.82,301.49,272.31+14*BAR,53,4.6,release=.095)

vocal('chorus 2 / refrain',308.64,328.13,308.84,56,2.85)
vocal('chorus 2 / extension',308.64,329.85,308.84,68,2.75)

# Let the beat answer the last hook, then ease its 808 back under the sung coda.
coda_bar=82
coda_downbeat=GRID+coda_bar*BAR
coda_start=coda_downbeat+1.5*BEAT
outro_slice=slice(sample(coda_downbeat-BAR),len(bed))
outro_time=np.arange(outro_slice.start,len(bed))/SR
outro_shape=np.sin(np.pi/2*np.clip((outro_time-coda_downbeat+BAR)/BAR,0,1))**2
outro_bass=signal.sosfiltfilt(low,bed[outro_slice],axis=0)
bed[outro_slice]-=(outro_bass*(1-db(-2.8))*outro_shape[:,None]).astype(np.float32)
bed[-sample(.015):]*=np.cos(np.linspace(0,np.pi/2,sample(.015),dtype=np.float32))[:,None]**2

coda_bounds=(14.30,27.87)
coda=take(load(P/'stems'/'only_one_open_vocals.wav'),*coda_bounds)
with TemporaryDirectory(prefix='only-one-coda-') as folder:
    raw=Path(folder)/'raw.wav'
    tuned=Path(folder)/'tuned.wav'
    sf.write(raw,coda,SR,subtype='FLOAT')
    subprocess.run(['rubberband','-q','-3','-F','--centre-focus','-p','-1',
                    str(raw),str(tuned)],check=True)
    coda=load(tuned)
coda=filt(coda.mean(axis=1,keepdims=True),'highpass',125)
coda=PeakFilter(cutoff_frequency_hz=2750,gain_db=.8,q=.85)(coda.T.copy(),SR).T
coda=Compressor(threshold_db=-24,ratio=2,attack_ms=12,release_ms=110)(coda.T.copy(),SR).T
coda=np.repeat(fade(coda,.065,.18),2,axis=1)
# Keep the quieter closing voice tucked just below the preceding hook.
band=filt(coda,'bandpass',(600,4100))
frames=band[:len(band)//2646*2646].reshape(-1,2646,2)
levels=np.mean(frames**2,axis=(1,2))
active=levels>np.percentile(levels,75)*.22
coda*=db(-33.5)/np.sqrt(np.mean(levels[active]))
put(voice,coda,coda_start)
put(fx,room(coda,size=.47)*.18,coda_start)
events.append(dict(name='outro / Only One',at=coda_start,stop=coda_start+len(coda)/SR,
                   source_bounds=coda_bounds,pitch_semitones=-1))

# Make room for consonants in the beat while leaving the kick and the 808 pulse intact.
hop=sample(.025)
count=len(voice)//hop
speech=filt(voice,'bandpass',(850,4100))
r=np.mean(speech[:count*hop].reshape(count,hop,2)**2,axis=(1,2))
r=ndimage.gaussian_filter1d(r,5.2)
activity=np.clip(np.sqrt(r)/.057,0,1)
gain=np.interp(np.arange(len(voice)),(np.arange(count)+.5)*hop,activity).astype(np.float32)
mid=signal.butter(2,(1150,3550),btype='bandpass',fs=SR,output='sos')
presence=signal.sosfiltfilt(mid,bed,axis=0).astype(np.float32)
bed-=presence*gain[:,None]*.18

mix=bed+voice+fx
assert len(mix)==len(beat) and np.isfinite(mix).all()
mix_path=P/'premaster.wav'
sf.write(mix_path,mix,SR,subtype='FLOAT')
sf.write(P/'vocal_check.wav',voice,SR,subtype='FLOAT')
sf.write(P/'instrumental_check.wav',bed,SR,subtype='FLOAT')
(P/'arrangement.json').write_text(json.dumps({'bpm':138,'duration':len(beat)/SR,'events':events},indent=2))
print(json.dumps(events,indent=2),flush=True)

def loudness(path):
    cmd=['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',
         'loudnorm=I=-13.5:TP=-1.4:LRA=7:print_format=json','-f','null','-']
    log=subprocess.run(cmd,check=True,capture_output=True,text=True).stderr
    return json.loads(re.findall(r'\{[^{}]+\}',log)[-1])

# Match the gain used for the approved edit so the main arrangement stays identical.
gain=.76
out=P/'candidate_outro.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(mix_path),'-af',
    f'volume={gain:.3f}dB,aresample=96000,alimiter=limit=0.839:attack=5:release=76:level=false:latency=true,aresample=44100',
    '-metadata','title=For the Kids (v3)','-metadata','artist=Kanye West × Yeat',
    '-c:a','libmp3lame','-b:a','320k',str(out)],check=True)
post=loudness(out)
assert float(post['input_tp'])<=-1.0
print('Master',post,flush=True)
