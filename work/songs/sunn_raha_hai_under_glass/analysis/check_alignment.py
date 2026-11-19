from pathlib import Path
import json

import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mido
import numpy as np
from scipy import signal
import soundfile as sf

P=Path(__file__).resolve().parent.parent
A=P/'analysis'
S=P/'stems/arrangement'
grid=json.loads((A/'arrangement.json').read_text())
beat=60/grid['bpm']
phase=grid['phase_in_source_seconds']
source_beats=np.load(A/'source-beats.npz')['beats']
source_beats=source_beats[(source_beats>.9)&(source_beats<205)]
d=source_beats-phase
d=d-np.rint(d/beat)*beat
alignment={'source_beat_positions_checked':len(d),
           'source_grid_median_error_ms':float(1000*np.median(abs(d))),
           'source_grid_p95_error_ms':float(1000*np.percentile(abs(d),95))}
assert alignment['source_grid_p95_error_ms']<35

def read(path):
    x,sr=sf.read(path,dtype='float32',always_2d=True)
    return x.mean(axis=1),sr

def lpf(x,sr,cut,kind='bandpass'):
    return signal.sosfilt(signal.butter(3,cut,btype=kind,fs=sr,output='sos'),x)

def find_attack(x,sr,around):
    a=round((around-.045)*sr)
    b=round((around+.095)*sr)
    smoothed=signal.convolve(x[a:b]**2,np.ones(90)/90,mode='same')
    peak=smoothed.max()
    attack=np.flatnonzero(smoothed>peak*.22)[0]
    return (a+attack)/sr, float(peak)

drums,sr=read(S/'drums.wav')
kick=lpf(drums,sr,[33,100])
differences=[]
for section in grid['sections']:
    if section['name'] not in {'chorus','chorus2'}:
        continue
    for at in np.arange(section['start'],section['end']-.10,4*beat):
        found,peak=find_attack(kick,sr,at)
        assert peak>.003
        differences.append(1000*(found-at))
assert len(differences)>=10
alignment['chorus_downbeats_checked']=len(differences)
alignment['chorus_kick_p95_offset_ms']=float(np.percentile(abs(np.asarray(differences)),95))
assert alignment['chorus_kick_p95_offset_ms']<31

voice,sr=read(S/'vocal.wav')
source,source_sr=read(P/'stems/htdemucs/source/vocals.wav')
assert source_sr==sr
offsets=[]
cues=grid['vocal_cues']
for cue in cues:
    expected=cue['mix_start']-cue['source_start']
    lower, upper=cue['source_start'],cue['source_end']
    for lo in np.linspace(lower+3,upper-3,6):
        a=round(lo*sr)
        b=a+round(.82*sr)
        chunk=lpf(source[a:b],sr,[300,3400])
        buffer_start=round((lo+expected-.05)*sr)
        test=lpf(voice[buffer_start:buffer_start+len(chunk)+round(.10*sr)],sr,[300,3400])
        lag=signal.correlate(test,chunk,mode='valid',method='fft').argmax()
        offsets.append((buffer_start+lag-a)/sr-expected)
intro_end=round(cues[0]['mix_start']*sr)
interlude_a=round((cues[0]['mix_start']+cues[0]['source_end']-cues[0]['source_start']+.035)*sr)
interlude_b=round(cues[1]['mix_start']*sr)
assert np.max(np.abs(voice[:intro_end]))==0
assert np.max(np.abs(voice[interlude_a:interlude_b]))<1.e-5
alignment['vocal_free_intro_seconds']=intro_end/sr
alignment['vocal_free_interlude_seconds']=(interlude_b-interlude_a)/sr
alignment['vocal_passages_checked']=len(offsets)
alignment['vocal_max_offset_from_placement_ms']=float(1000*np.max(abs(np.asarray(offsets))))
assert alignment['vocal_max_offset_from_placement_ms'] < 4

def midi_notes(path):
    now=0.
    active={}
    notes=[]
    for msg in mido.MidiFile(path):
        now+=msg.time
        if msg.type=='note_on' and msg.velocity>0:
            active[msg.note]=now
        elif msg.type in {'note_off','note_on'} and msg.note in active:
            notes.append((active.pop(msg.note),now,msg.note))
    return notes

def freq(note):
    return 440*2**((note-69)/12)

def rendered_pitch(data,sr,span):
    start,stop,n=span
    clip=data[round(sr*(start+.026)):round(sr*min(stop,start+.19))]
    if len(clip)<round(.05*sr):
        return None
    target=freq(n)
    z=np.abs(np.fft.rfft(clip*np.hanning(len(clip)),n=32768))
    f=np.fft.rfftfreq(32768,1/sr)
    area=(f>target*.935)&(f<target*1.075)
    hz=f[area][np.argmax(z[area])]
    return 1200*np.log2(hz/target)

keys,sr=read(S/'clean_left-dry.wav')
notes=midi_notes(P/'midi/clean_left.mid')
pitch=[v for n in notes if (v:=rendered_pitch(keys,sr,n)) is not None]
bass,_=read(S/'picked_bass-dry.wav')
bn=midi_notes(P/'midi/picked_bass.mid')
# The low fundamentals are resolved over a longer pitch window.
def bass_pitch(span):
    a,b,n=span
    if b-a<.49:
        return None
    clip=bass[round(sr*(a+.10)):round(sr*min(b,a+.55))]
    z=np.abs(np.fft.rfft(clip*np.hanning(len(clip)),n=131072))
    f=np.fft.rfftfreq(131072,1/sr)
    expected=freq(n)
    mask=(f>expected*.90)&(f<expected*1.10)
    return 1200*np.log2(f[mask][np.argmax(z[mask])]/expected)
bp=[v for n in bn if (v:=bass_pitch(n)) is not None]
for name,values in [('clean_guitar',pitch),('held_bass',bp)]:
    alignment[name+'_notes_checked']=len(values)
    alignment[name+'_within_quarter_semitone_pct']=float(100*np.mean(np.abs(values)<25))
assert alignment['clean_guitar_within_quarter_semitone_pct']>94
assert alignment['held_bass_within_quarter_semitone_pct']>90
(A/'alignment.json').write_text(json.dumps(alignment,indent=2))
print(json.dumps(alignment,indent=2))

end=16
y=signal.resample_poly(keys[:round(sr*(end+.25))],1,2)
sr//=2
hop=128
cq=abs(librosa.cqt(y,sr=sr,hop_length=hop,fmin=librosa.midi_to_hz(48),
                   n_bins=42,tuning=0))
time=np.arange(cq.shape[1])*hop/sr
plt.style.use('dark_background')
fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
im=ax.pcolormesh(time,np.arange(48,90),20*np.log10(np.maximum(cq,1.e-7)),
                  vmin=-64,vmax=-14,shading='nearest',cmap='magma')
for a,b,n in notes:
    if a<end:
        ax.hlines(n,a,b,color='#8efbeb',linewidth=1.3)
ax.set(xlim=(0,end),ylim=(52,87),title='Clean electric guitar | score and rendered pitches',
       xlabel='Time (s)',ylabel='MIDI pitch')
fig.colorbar(im,ax=ax,label='CQT level (dB relative to unit magnitude)')
fig.savefig(A/'guitar-midi.png',dpi=118)
