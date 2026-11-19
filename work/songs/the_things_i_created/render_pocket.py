from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal
from pedalboard import Compressor, Pedalboard, PeakFilter, Reverb

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
ki,kg,kc=split('wonder_grind',wonder,151)
ci,cg,cc=split('coffee_verse',coffee,95)
ti,tg,tc=split('coffee_remorse',coffee,119)
kkeys=load(P/'stems/htdemucs/wonder_verse_instrumental/other.wav')

coffee_start=C0-HANDOFF
length=sample(DURATION)
music=np.zeros((length,2),np.float32)
kanye=np.zeros_like(music)
travis=np.zeros_like(music)
details=np.zeros_like(music)

# Use the uninterrupted Coffee Bean performance under both vocalists.
# The two separation passes overlap before the first retained Travis word.
over=.46
native=cut(coffee,coffee_start,C_TURN+over)
nt=coffee_start+np.arange(len(native))/SR
first=cut(ci,coffee_start,123.2,95)
later=cut(ti,120.95,C_TURN+over,119)
offset=sample(120.95-coffee_start)
assert offset+len(later)<=len(native)+1
music_head=native.copy()
music_head[:len(first)]=first
fade_parts=shaped(nt[offset:offset+len(later)],[(121.00,0),(123.05,1)])
n=min(len(later),len(native)-offset)
music_head[offset:offset+n]+=(later[:n]-music_head[offset:offset+n])*fade_parts[:n,None]
# Return to the native album sum once the selected, independently timed words end.
restore=shaped(nt,[(146.20,0),(147.07,1)])
music_head+=(native-music_head)*restore[:,None]
room_to_start=shaped(nt,[(coffee_start,.75),(coffee_start+BAR, .92),(coffee_start+2*BAR,1)])
# A small pullback gives the last line room before the chord-matched string turn.
to_strings=shaped(nt,[(C_TURN-1.45,1),(C_TURN-.13,.84),(C_TURN+over,0)])
bed_gain=1.0
add(music,fade(music_head*(room_to_start*to_strings)[:,None],.036,0),0,bed_gain)

def voice_split(raw,back,origin,lo,hi):
    return cut(raw,lo,hi)-cut(back,lo,hi,origin)

def lead_tone(x,tilt):
    x=filt(x,'highpass',95)
    return Pedalboard([PeakFilter(cutoff_frequency_hz=2270,q=.75,gain_db=tilt),
        Compressor(threshold_db=-20,ratio=1.43,attack_ms=16,release_ms=96)])(x.T.copy(),SR).T

# Kanye's grind/skyline run has fewer long pauses than the last preview.
k_grid=170.61-6*240/K_BPM
klo,khi=155.54,173.03
k=voice_split(wonder,ki,151,klo,khi)
k=stretch(k,(khi-klo)*KR,'cinema_grind_continuous_95')
k=fade(lead_tone(k,-.50),.012,.057)
kat=2*BAR+(klo-k_grid)*KR+.007
k_inst=body(region(music,kat+.31,kat+len(k)/SR-.35))
k*=k_inst*db(-.65)/max(body(k),1e-8)
add(kanye,k,kat)

# Slow only the denser Travis lines and reset the next entrance in a breath.
phrases=[
    (124.33,128.52,1.025,-.035),
    (129.49,136.48,1.048,-.082),
    (136.96,145.85,1.035,-.034),
]
cues=[]
for i,(lo,hi,ratio,shift) in enumerate(phrases):
    v=voice_split(coffee,ti,119,lo,hi)
    v=stretch(v,(hi-lo)*ratio,f'cinema_coffee_pocket_line_{i+1}')
    v=fade(lead_tone(v,.3),.013,.057)
    at=HANDOFF+lo-C0+shift
    cues.append((round(at,4),round(at+len(v)/SR,4),ratio))
    add(travis,v,at)
assert all(a[1]<b[0] for a,b in zip(cues,cues[1:])),cues
v_lo,v_hi=cues[0][0],cues[-1][1]
travis*=body(region(music,v_lo+.29,v_hi-.45))*db(-.60)/max(body(region(travis,v_lo+.29,v_hi-.45)),1e-8)

# The same cello tone frames both voices and returns in the full strings.
f=trim_note(cut(coffee,176.46,177.66),174.)
f=fade(f,.24,.29)
f*=db(-27)/max(body(f),1e-8)
add(details,f,.57)
add(details,wet(f),.57,.24)
c=trim_note(cut(coffee,186.39,187.38),131.)
c=fade(c,.18,.23)
c*=db(-26.5)/max(body(c),1e-8)
add(details,c,HANDOFF-.36)
add(details,wet(c),HANDOFF-.36,.24)
# Use C from Kanye's string/synth bed in the last Kanye bar, where the C-minor
# backing and F-major source both contain that note.
reply=trim_note(cut(kkeys,190.78,192.19,169),261.63)
reply=fade(reply,.25,.34)
reply*=db(-26.8)/max(body(reply),1e-8)
add(details,reply,HANDOFF-1.40)

# Build the lift from the same D-flat harmony and keep its recorded drums.
lead=.20
late=cut(coffee,STRING_START-lead,STRING_END)
u=np.arange(len(late))/SR-lead
late*=shaped(u,[(-lead,0),(.38,1),(STRING_END-STRING_START-.68,1),
                  (STRING_END-STRING_START,0)])[:,None]
add(music,late,TURN-lead,db(.25))
# Kanye's F-major chord returns transposed to a compatible Ab-major color.
k_chord=cut(kkeys,190.89,192.23,169)
k_chord=filt(filt(pitch(k_chord,3),'highpass',210),'lowpass',2500)
k_chord=fade(k_chord,.25,.38)
k_chord*=db(-26)/max(body(k_chord),1e-8)
add(details,k_chord,TURN+(187.20-STRING_START))
add(details,wet(k_chord),TURN+(187.20-STRING_START),.20)

lead_mix=kanye+travis
room_bus=wet(lead_mix)[:length]*.065
mix=music+lead_mix+room_bus+details
assert np.isfinite(mix).all()
wave=P/'what_it_cost_pocket.wav'
sf.write(wave,mix,SR,subtype='FLOAT')
sf.write(P/'pocket_music_check.wav',music,SR,subtype='FLOAT')
sf.write(P/'pocket_vocal_check.wav',lead_mix,SR,subtype='FLOAT')
before=loudness(wave)
gain=-14.2-float(before['input_i'])
out=P/'what_it_cost_pocket.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(wave),'-af',
     f'volume={gain:.4f}dB,aresample=96000,alimiter=limit=0.82:attack=5:release=74:level=false:latency=true,aresample=44100',
     '-metadata','title=What It Cost (I Wonder × Coffee Bean, revised preview)',
     '-c:a','libmp3lame','-b:a','320k',str(out)],check=True)
after=loudness(out)
assert float(after['input_tp'])<-.9
report=dict(bpm=BPM,kanye_start=kat,kanye_end=kat+len(k)/SR,first_travis_edit=cues[0],
            travis_lines=cues,string_turn=TURN,duration=len(mix)/SR,stem_alignment=[kc,cc,tc],
            integrated_lufs=after['input_i'],true_peak=after['input_tp'])
(P/'pocket_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
