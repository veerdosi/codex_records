from pathlib import Path
import argparse
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

sys.path.insert(0,str(P/'alternate'))
from render import warp

args=argparse.ArgumentParser()
args.add_argument('--travis-anchor',type=float,default=44.575)
args.add_argument('--travis-end',type=float,default=79.99)
args.add_argument('--kanye-end',type=float,default=195.49)
args.add_argument('--tag',default='extended')
args=args.parse_args()

BPM=95
BEAT=60/BPM
BAR=4*BEAT
K_BPM=95.7
KR=K_BPM/BPM
C0=196*BEAT
HOOK0=128*BEAT
STRING_START=288*BEAT
STRING_END=208.83
PIANO_BARS=2
GROOVE_INTRO_BARS=4
TRAVIS_BAR=6
HOOK_1=21
KANYE_BAR=25
HOOK_2=41
STRINGS_BAR=46
DURATION=STRINGS_BAR*BAR+STRING_END-STRING_START+.20

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
ki,_,kc=split('wonder_grind',wonder,151)
ki_late,_,klc=split('wonder_verse',wonder,169)
ci,_,cc=split('coffee_verse',coffee,95)
vi,_,vc=split('coffee_remorse',coffee,119)
hi,_,hc=split('coffee_hook',coffee,76)
keys=load(P/'stems/htdemucs/wonder_verse_instrumental/other.wav')

N=sample(DURATION)
backing=np.zeros((N,2),np.float32)
singers=np.zeros_like(backing)
kanye=np.zeros_like(backing)
travis=np.zeros_like(backing)
details=np.zeros_like(backing)

def layer_at(bus,x,bar,pre):
    """Cross before the incoming downbeat, leaving the attack fully open."""
    i=sample(bar*BAR-pre)
    assert i>=0 and i+len(x)<=N
    t=np.arange(len(x))/SR
    ramp=shaped(t,[(0,0),(pre-.010,1)])
    bus[i:i+len(x)]+= (x-bus[i:i+len(x)])*ramp[:,None]

def band_tone(x,lo,hi):
    b=signal.butter(2,(lo,hi),btype='bandpass',fs=SR,output='sos')
    return signal.sosfiltfilt(b,x,axis=0).astype(np.float32)

def stitched_back(lo,stop):
    x=cut(ci,lo,min(123.45,stop),95)
    if stop<=123.45:
        return x
    bridge_at=121.05
    after=cut(vi,bridge_at,stop,119)
    i=sample(bridge_at-lo)
    n=len(x)-i
    after[:n]=x[i:]+(after[:n]-x[i:])*shaped(np.arange(n)/SR,[(.04,0),(2.22,1)])[:,None]
    return np.concatenate([x[:i],after])

coffee_start=C0-11*BAR
kanye_source_start=coffee_start+GROOVE_INTRO_BARS*BAR
intro_end=coffee_start+GROOVE_INTRO_BARS*BAR
intro=stitched_back(coffee_start,intro_end)
t=np.arange(len(intro))/SR
low=filt(intro,'lowpass',1720)
open_colour=shaped(t,[(0,.36),(.79,.63),(2.7,.88),(4*BAR-.10,1)])
level_curve=shaped(t,[(0,.67),(1.6,.92),(3.5,1)])
intro=(low+(intro-low)*open_colour[:,None])*level_curve[:,None]
add(backing,fade(intro,.045,0),PIANO_BARS*BAR)

# Give the piano room for an entire phrase and let the last notes ring over the groove.
sample_source=load(P/'alternate'/'coltrane.wav')
piano=warp(cut(sample_source,1.405,8.70),.953,-3)
piano=filt(filt(piano,'highpass',123),'lowpass',5300)
piano=fade(piano,.030,.61)
piano*=db(-19.7)/body(piano)
add(details,piano,.13)
add(details,wet(piano),.13,.15)
answer=fade(cut(piano,0,1.55),.045,.42)
add(details,answer,TRAVIS_BAR*BAR-1.92,.34)
add(details,wet(answer),TRAVIS_BAR*BAR-1.92,.10)
add(details,answer,HOOK_1*BAR-1.68,.48)
add(details,wet(answer),HOOK_1*BAR-1.68,.10)

def native_section(bar,n_bars,start,inst,origin,gates,gain_db=0):
    # Recombine on the original sample clock. Where the vocal gate is open,
    # the backing and lead sum exactly to the album performance.
    pre=.081
    a,b=start-pre,start+n_bars*BAR
    body_audio=cut(inst,a,b,origin)
    raw=cut(coffee,a,b)
    t=a+np.arange(len(raw))/SR
    g=shaped(t,gates)
    gain=db(gain_db)
    layer_at(backing,body_audio*gain,bar,pre)
    layer_at(singers,(raw-body_audio)*(g*gain)[:,None],bar,pre)

hook_gate=[(81.635,0),(81.770,1),(88.22,1),(88.315,0)]
pre=.081
# Eight bars of the original groove bring the verse back to the same chord.
travis_gain=db(-.46)
layer_at(backing,cut(vi,C0-pre,C0+8*BAR,119)*travis_gain,TRAVIS_BAR,pre)
layer_at(backing,cut(vi,C0-pre,C0+7*BAR,119)*travis_gain,TRAVIS_BAR+8,pre)

# The Coffee Bean kick leans into 2.50; the HYAENA break leans into 2.75.
# Move part of that accent on alternate bars and leave the snare untouched.
drums=load(P/'stems'/'htdemucs'/'coffee_remorse_instrumental'/'drums.wav')
kick_band=filt(drums,'bandpass',(37,370))
for bar in range(1,HOOK_1-TRAVIS_BAR-1):
    source_bar=C0+(bar%8)*BAR
    dest_bar=(TRAVIS_BAR+bar)*BAR
    if bar%2==0:
        kick_at=2.50*BEAT
        kick=fade(cut(kick_band,source_bar+kick_at-.012-119,
                      source_bar+kick_at+.117-119),.012,.041)
        add(backing,kick,-.012+dest_bar+kick_at,-.43*travis_gain)
        add(backing,kick,-.010+dest_bar+2.75*BEAT,.50*travis_gain)
    if bar%4!=3:
        kick=fade(cut(kick_band,source_bar-.010-119,source_bar+.095-119),.010,.041)
        add(backing,kick,-.010+dest_bar+.50*BEAT,.26*travis_gain)

native_section(HOOK_1,4,HOOK0,hi,76,hook_gate,-.58)
kanye_bed=stitched_back(kanye_source_start-pre,kanye_source_start+(HOOK_2-KANYE_BAR)*BAR)
layer_at(backing,kanye_bed,KANYE_BAR,pre)

# Align the lead to the drum phase from its source and retain the performance's internal timing.
ha,hb=46.063,args.travis_end
hr=97/95
h=cut(load(P/'alternate'/'hyaena_long_vocals.wav'),ha,hb,42)
h=stretch(h,(hb-ha)*hr,f'hyaena_long_95_{hb:.3f}')
h=filt(h,'highpass',93)
h=Pedalboard([PeakFilter(cutoff_frequency_hz=2870,q=.80,gain_db=-.6),
              Compressor(threshold_db=-20,ratio=1.6,attack_ms=16,release_ms=112)])(h.T.copy(),SR).T
h=fade(h,.026,.10)
h_at=TRAVIS_BAR*BAR+(ha-args.travis_anchor)*hr
h_end=h_at+len(h)/SR
assert TRAVIS_BAR*BAR-.38<=h_at and h_end<HOOK_1*BAR+.55,(h_at,h_end)
h*=body(region(backing,h_at+.19,min(h_end,HOOK_1*BAR)))*db(-1.85)/max(body(h),1e-8)
add(travis,h,h_at)

# Use the contiguous Kanye performance and blend the two estimates in their overlapping source audio.
k0=170.61-6*240/K_BPM
ka,kb=156.425,args.kanye_end
pivot=171.75
k_main=cut(ki,ka,174.65,151)
k_late=cut(ki_late,pivot,kb,169)
i=sample(pivot-ka)
n=len(k_main)-i
blend=shaped(np.arange(n)/SR,[(0,0),(n/SR-.02,1)])
k_late[:n]=k_main[i:]+(k_late[:n]-k_main[i:])*blend[:,None]
k_music=np.concatenate([k_main[:i],k_late])
source_k=cut(wonder,ka,ka+len(k_music)/SR)-k_music
k=stretch(source_k,len(source_k)/SR*KR,f'extended_wonder_clean_95_{kb:.3f}')
k=Pedalboard([PeakFilter(cutoff_frequency_hz=2240,q=.77,gain_db=-.5),
              Compressor(threshold_db=-21,ratio=1.42,attack_ms=18,release_ms=95)])(filt(k,'highpass',93).T.copy(),SR).T
k=fade(k,.009,.08)
k_at=KANYE_BAR*BAR+(ka-k0)*KR+.007
k_end=k_at+len(k)/SR
assert k_end<HOOK_2*BAR+.48,(k_end,HOOK_2*BAR)
k*=body(region(backing,k_at+.19,HOOK_2*BAR-.22))*db(-.82)/max(body(k),1e-8)
add(kanye,k,k_at)

native_section(HOOK_2,5,HOOK0,hi,76,hook_gate,-.12)

# Let the returning hook widen with a restrained string layer from Kanye.
# Fmaj7 moved down two semitones is Ebmaj7, which shares Eb/G/Bb with Cm7.
k_lift=cut(keys,190.88,192.37,169)
k_lift=filt(filt(pitch(k_lift,-2),'highpass',205),'lowpass',2880)
k_lift=fade(k_lift,.37,.46)
k_lift*=db(-24.75)/max(body(k_lift),1e-8)
for source_at,gain in [(83.12,.87),(86.11,1.)]:
    t=HOOK_2*BAR+source_at-HOOK0
    add(details,k_lift,t,gain)
    add(details,wet(k_lift),t,gain*.23)

# The common C note gives the opening and both changes the same color.
c=trim_note(cut(coffee,186.36,187.41),131.)
c=fade(c,.19,.28)
c*=db(-26.4)/max(body(c),1e-8)
for t,gain in [(PIANO_BARS*BAR+.49,.72),(HOOK_1*BAR-.60,.83),(KANYE_BAR*BAR-.52,.73)]:
    add(details,c,t,gain)
    add(details,wet(c),t,.18*gain)

# On the last D-flat bar, follow the real string performance to its release.
pre=.090
strings=cut(coffee,STRING_START-pre,STRING_END)
u=np.arange(len(strings))/SR+STRING_START-pre
tail=shaped(u,[(203.6,1),(205.64,.91),(208.8,0)])
layer_at(backing,strings*tail[:,None],STRINGS_BAR,pre)

# The reprise changes the apparent size of the room while the groove keeps
# moving. Work on the backing's upper stereo information only.
a=sample(HOOK_2*BAR-1.34)
b=sample(STRINGS_BAR*BAR+2.0)
t=np.arange(a,b)/SR-HOOK_2*BAR
side=backing[a:b]-backing[a:b].mean(axis=1,keepdims=True)
wide=band_tone(side,235,9600)
width=shaped(t,[(-1.34,1),(-.57,.47),(-.16,.51),(.95,1.15),
                (2.0,1.22),(8.3,1.16),(STRINGS_BAR*BAR-HOOK_2*BAR+.48,1.20),
                (STRINGS_BAR*BAR-HOOK_2*BAR+1.9,1)])
backing[a:b]+=wide*(width-1)[:,None]

# Keep the natural Travis vocal-to-beat alignment and share a subtle room
# with Kanye so the blend has a common perspective.
mix=backing+singers+kanye+travis+details+wet(kanye+singers+travis)[:N]*.041
assert np.isfinite(mix).all()
wave=P/f'{args.tag}_mix.wav'
sf.write(wave,mix,SR,subtype='FLOAT')
sf.write(P/f'{args.tag}_backing_check.wav',backing,SR,subtype='FLOAT')
sf.write(P/f'{args.tag}_vocal_check.wav',kanye+singers+travis,SR,subtype='FLOAT')
stats=loudness(wave)
gain=-14.2-float(stats['input_i'])
out=P/f'{args.tag}_candidate.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(wave),'-af',
     f'volume={gain:.4f}dB,aresample=96000,alimiter=limit=0.82:attack=5:release=74:level=false:latency=true,aresample=44100',
     '-metadata','title=What It Cost','-metadata','artist=Kanye West × Travis Scott',
     '-c:a','libmp3lame','-b:a','320k',str(out)],check=True)
after=loudness(out)
assert float(after['input_tp'])<-.9
report=dict(bpm=BPM,kanye_source_bounds=[ka,kb],kanye_start=k_at,kanye_end=k_end,
            hook_1=HOOK_1*BAR,travis_verse=TRAVIS_BAR*BAR,hook_2=HOOK_2*BAR,
            travis_start=h_at,travis_end=h_end,travis_source_bounds=[ha,hb],travis_anchor=args.travis_anchor,
            strings=STRINGS_BAR*BAR,duration=N/SR,stem_alignment=[kc,klc,cc,vc,hc],
            integrated_lufs=after['input_i'],true_peak=after['input_tp'])
(P/f'{args.tag}_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
