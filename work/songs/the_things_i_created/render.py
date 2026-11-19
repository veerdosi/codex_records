from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal
from pedalboard import Pedalboard, Reverb

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from dsp import SR, db, fade, filt, load, stretch

BPM=95
BEAT=60/BPM
BAR=4*BEAT
K_BPM=95.7
KR=K_BPM/BPM
K0=170.61
C0=196*BEAT
HANDOFF=9*BAR
TURN=HANDOFF+11*BAR
C_TURN=C0+11*BAR
STRING_START=C_TURN+12*BAR
STRING_END=205.64
DURATION=TURN+STRING_END-STRING_START+.32

def sample(t):
    return round(t*SR)

def cut(x,a,b,origin=0):
    i=sample(a-origin)
    n=sample(b-a)
    assert 0<=i and i+n<=len(x),(a,b,origin)
    return x[i:i+n].copy()

def shaped(t,points):
    x,y=np.asarray(points).T
    i=np.clip(np.searchsorted(x,t)-1,0,len(x)-2)
    u=np.clip((t-x[i])/(x[i+1]-x[i]),0,1)
    return (y[i]+(y[i+1]-y[i])*(.5-.5*np.cos(np.pi*u))).astype(np.float32)

def level(x):
    return float(np.sqrt(np.mean(x*x)+1e-12))

def body(x):
    return level(filt(x,'bandpass',(150,5200)))

def add(x,y,t,gain=1.):
    i=sample(t)
    assert i>=0 and i+len(y)<=len(x)
    x[i:i+len(y)]+=y*gain

def region(x,a,b):
    return x[sample(a):sample(b)]

def split(name,raw,origin):
    vox=load(P/f'{name}_vocals.wav')
    inst=load(P/f'{name}_instrumental.wav')
    total=vox+inst
    original=raw[sample(origin):sample(origin)+len(total)]
    assert len(original)==len(total)
    gain=float(np.sum(total*original)/np.sum(total*total))
    corr=float(np.corrcoef(total[::8,0],original[::8,0])[0,1])
    assert corr>.985,(name,corr)
    return inst*gain,gain,corr

def trim_note(x,f0):
    # Preserve a real string note and its audible harmonics.
    y=np.zeros_like(x)
    for overtone in range(1,8):
        freq=overtone*f0
        width=max(7.,freq*.024)
        sos=signal.butter(2,(freq-width,freq+width),btype='bandpass',fs=SR,output='sos')
        y+=signal.sosfiltfilt(sos,x,axis=0).astype(np.float32)
    return y

def wet(x):
    x=np.pad(x,((0,sample(1.0)),(0,0)))
    fx=Pedalboard([Reverb(room_size=.44,damping=.74,dry_level=0,wet_level=1,width=.91)])
    return filt(filt(fx(x.T.copy(),SR).T,'highpass',235),'lowpass',5200)

def pitch(x,semitones):
    with tempfile.TemporaryDirectory(prefix='coffee-strings-') as path:
        a,b=(Path(path)/f for f in ['a.wav','b.wav'])
        sf.write(a,x*.5,SR,subtype='FLOAT')
        subprocess.run(['rubberband','-q','-3','--centre-focus','-p',str(semitones),str(a),str(b)],check=True)
        return 2*load(b)[:len(x)]

def loudness(path):
    log=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',
        'loudnorm=I=-14.2:TP=-1.3:LRA=8:print_format=json','-f','null','-'],
        check=True,capture_output=True,text=True).stderr
    return json.loads(re.findall(r'\{[^{}]+\}',log)[-1])

wonder=load(P/'wonder.wav')
coffee=load(P/'coffee.wav')
ki,kg,kc=split('wonder_verse',wonder,169)
ci,cg,cc=split('coffee_verse',coffee,95)
kdr=kg*load(P/'stems/htdemucs/wonder_verse_instrumental/drums.wav')
cdr=cg*load(P/'stems/htdemucs/coffee_verse_instrumental/drums.wav')
kkeys=kg*load(P/'stems/htdemucs/wonder_verse_instrumental/other.wav')

length=sample(DURATION)
kbed=np.zeros((length,2),np.float32)
cbed=np.zeros_like(kbed)
voices=np.zeros_like(kbed)
details=np.zeros_like(kbed)

# Original Kanye bars at their recorded phase, with only the selected verse opened.
kend=K0+(HANDOFF+.40)/KR
k_music=cut(ki,K0,kend,169)
k_raw=cut(wonder,K0,kend)
t=K0+np.arange(len(k_music))/SR
k_voice=(k_raw-k_music)*shaped(t,[(173.51,0),(173.66,1),(192.85,1),(193.06,0)])[:,None]
k_drums=cut(kdr,K0,kend,169)
k_music-=k_drums*shaped(t,[(K0,.15),(K0+1.24,0),(191.54,0),(192.16,.58),(193.0,.84)])[:,None]
k_music=stretch(k_music,(kend-K0)*KR,'cinema_wonder_bed_v1')
k_voice=stretch(k_voice,(kend-K0)*KR,'cinema_wonder_voice_v1')
tk=np.arange(len(k_music))/SR
# Keep the drums moving as the top of the Kanye backing makes room for the pivot.
front=shaped(tk,[(0,.77),(1.33,1)])
out=shaped(tk,[(HANDOFF-.65,1),(HANDOFF-.12,.67),(HANDOFF+.25,0)])
dark=filt(k_music,'lowpass',790)
shade=shaped(tk,[(HANDOFF-1.52,0),(HANDOFF-.42,.75),(HANDOFF+.27,.88)])
add(kbed,fade((k_music+(dark-k_music)*shade[:,None])*(front*out)[:,None],.048,0),0)
add(voices,k_voice*.91,0)

# Hear Travis's snare before the new harmony. Its backbeat is aligned to Kanye's.
coffee_drums=cut(cdr,C0-BAR,C0+.24,95)
t=np.arange(len(coffee_drums))/SR
filter_drums=filt(coffee_drums,'bandpass',(170,5000))
env=shaped(t,[(0,0),(.58,.38),(1.47,.72),(BAR-.31,.83),(BAR+.22,0)])
add(details,filter_drums*env[:,None],HANDOFF-BAR,.83)

# Travis enters with the original pickup. Fade in the instrumental while
# leaving the incoming voice on its original timing.
pre=.68
c_first=C0-pre
over=.49
raw_c=cut(coffee,c_first,C_TURN+over)
ct=c_first+np.arange(len(raw_c))/SR
overlap_source=cut(ci,c_first,126.3,95)
n=len(overlap_source)
travis_mask=shaped(ct[:n],[(124.37,0),(124.60,1)])
c_music=raw_c.copy()
c_music[:n]=overlap_source
c_voice=np.zeros_like(raw_c)
c_voice[:n]=(raw_c[:n]-overlap_source)*travis_mask[:,None]
# Use the original album mix after the handoff, with no later stem seam.
together=shaped(ct[:n],[(125.38,0),(126.28,1)])
c_music[:n]+=(raw_c[:n]-c_music[:n])*together[:,None]
c_voice[:n]*=1-together[:,None]
c_music[n:]=raw_c[n:]
env=shaped(ct,[(c_first,0),(C0-.09,.44),(C0+.39,1),(C_TURN-.20,1),(C_TURN+over,0)])
g=body(cut(wonder,181,190))/body(cut(coffee,129,140))
g=float(np.clip(g,.81,1.14))
add(cbed,c_music*env[:,None],HANDOFF-pre,g)
add(voices,c_voice,HANDOFF-pre,g)

# A common tone from the actual cello appears early and at the handoff.
# F works over Kanye's opening F-major color; C works on both sides of the pivot.
f=trim_note(cut(coffee,176.46,177.66),174.)
f=fade(f,.21,.27)
f*=db(-26.3)/max(body(f),1e-8)
add(details,f,.49)
add(details,wet(f),.49,.24)
c=trim_note(cut(coffee,186.39,187.38),131.)
c=fade(c,.19,.22)
c*=db(-27.2)/max(body(c),1e-8)
add(details,c,HANDOFF-.62)
add(details,wet(c),HANDOFF-.62,.22)

# Pull the late strings forward by twelve whole bars at a D-flat harmony.
# Let the groove carry through that edit and leave the real recorded outro intact.
lead=.20
late=cut(coffee,STRING_START-lead,STRING_END)
u=np.arange(len(late))/SR-lead
late*=shaped(u,[(-lead,0),(.30,1),(STRING_END-STRING_START-.65,1),
                  (STRING_END-STRING_START,0)])[:,None]
add(cbed,late,TURN-lead,g)
# Kanye's last chord returns as a soft answer in the F-minor part of the lift.
# Fmaj7 raised three semitones gives Abmaj7, whose tones fit the F-minor color.
k_chord=cut(kkeys,190.89,192.23,169)
k_chord=filt(filt(pitch(k_chord,3),'highpass',210),'lowpass',2500)
k_chord=fade(k_chord,.30,.45)
k_chord*=db(-27.2)/max(body(k_chord),1e-8)
add(details,k_chord,TURN+(187.20-STRING_START))
add(details,wet(k_chord),TURN+(187.20-STRING_START),.17)

mix=kbed+cbed+voices+details
assert np.isfinite(mix).all()
premaster=P/'what_it_cost_preview.wav'
sf.write(premaster,mix,SR,subtype='FLOAT')
before=loudness(premaster)
gain=-14.2-float(before['input_i'])
out=P/'what_it_cost_preview.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(premaster),'-af',
     f'volume={gain:.4f}dB,aresample=96000,alimiter=limit=0.82:attack=5:release=74:level=false:latency=true,aresample=44100',
     '-metadata','title=What It Cost (I Wonder × Coffee Bean)','-c:a','libmp3lame','-b:a','320k',str(out)],check=True)
after=loudness(out)
assert float(after['input_tp'])<-.9
report=dict(bpm=BPM,kanye_source_start=K0,travis_source_bar=C0,first_handoff=HANDOFF,
            travis_pickup=HANDOFF+124.66-C0,string_turn=TURN,
            string_start=STRING_START,duration=len(mix)/SR,source_stem_alignment=[kc,cc],
            integrated_lufs=after['input_i'],true_peak=after['input_tp'])
(P/'render_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
