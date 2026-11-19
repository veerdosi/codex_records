"""Inspect level-matched rendered mixes and check the isolated parts."""
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

here = Path(__file__).resolve().parent
song = here.parents[1]
previous = song/'stems/arrangement'
sections = json.loads((song/'analysis/arrangement.json').read_text())['sections']
rate = 44100
beat = 60/85.42

def read(path, start=0., end=None):
    with sf.SoundFile(path) as file:
        assert file.samplerate == rate
        file.seek(round(start*rate))
        length = -1 if end is None else round(end*rate)-round(start*rate)
        return file.read(length, dtype='float32', always_2d=True)

def band(data, lo, hi):
    sos=signal.butter(3,[lo,hi],btype='bandpass',fs=rate,output='sos')
    return signal.sosfilt(sos,data,axis=0)

def db(power):
    return 10*np.log10(np.maximum(power,1e-12))

def framed(data, size):
    count=len(data)//size*size
    return np.mean(data[:count].reshape(-1,size)**2,axis=1)

def onset(audio, expected):
    start=round((expected-.024)*rate)
    end=round((expected+.088)*rate)
    x=audio[start:end]
    energy=np.convolve(x*x, np.ones(180)/180, mode='same')
    candidates=np.flatnonzero(energy>np.max(energy)*.12)
    return (start+candidates[0])/rate

mix=read(here/'Premaster.wav')
old=read(previous/'premaster.wav')
backing=read(here/'Backing.wav')
voice=read(here/'Voice.wav')
drums=read(here/'Drums.wav')
guitar=read(here/'Guitars.wav')
bass=read(song/'stems/shoegaze/Picked bass.wav')
old_voice=read(previous/'vocal.wav')
old_bed=read(previous/'backing.wav')
assert all(x.shape==mix.shape for x in (old,backing,voice,drums,guitar,bass,old_voice,old_bed))
assert np.max(abs(mix-voice-backing))<1e-6
assert np.max(abs(mix))<1
reports={}
peak_frame=round(.12*rate)
band_voice=band(voice.mean(axis=1),900,3800)
band_back=band(backing.mean(axis=1),900,3800)
band_old_voice=band(old_voice.mean(axis=1),900,3800)
band_old_bed=band(old_bed.mean(axis=1),900,3800)

for part in sections:
    start,end,name=part['start'],part['end'],part['name']
    a,b=(round(t*rate) for t in (start,end))
    vp=framed(band_voice[a:b],peak_frame)
    bp=framed(band_back[a:b],peak_frame)
    ov=framed(band_old_voice[a:b],peak_frame)
    ob=framed(band_old_bed[a:b],peak_frame)
    active=(vp>max(1e-6,np.max(vp)*.075))
    if active.any():
        margin=db(vp)-db(bp)
        old_margin=db(ov)-db(ob)
        # Check that the metric responds to a known 3 dB fader move at fixed frames.
        assert np.allclose((db(vp*10**.3)-db(bp))[active]-margin[active],3,atol=.001)
        difference=[np.round(np.percentile(v[active],[10,50]),2).tolist() for v in (old_margin,margin)]
    else:
        difference=None
    reports[name]={
        'start_s':round(start,3),'end_s':round(end,3),
        'vocal_midband_margin_db_p10_median_before_after':difference,
        'new_backing_rms_db':round(float(db(np.mean(backing[a:b]**2))),2),
    }

# Each chorus downbeat was scored as a kick. Recover the timing from its
# low band, comparing the new recording's lag with its other bar downbeats.
drum_low=band(drums.mean(axis=1),37,130)
for name in ('chorus','chorus2'):
    times=np.arange(reports[name]['start_s'], reports[name]['end_s']-.1,4*beat)
    errors=[1000*(onset(drum_low,t)-t) for t in times]
    reports[name]['kick_offset_from_grid_ms']=[round(e,1) for e in errors]
    assert max(abs(e) for e in errors)<35
# A deliberate 30 ms delay should be recovered on a single kick.
one=reports['chorus']['start_s']
offset=round(.030*rate)
shifted=np.pad(drum_low[:-offset],(offset,0))
assert abs((onset(shifted,one+.030)-onset(drum_low,one))-.030)<.001

# Inspect the new bass pitches against the MIDI near both refrain landings.
mid=mido.MidiFile(song/'midi/shoegaze/Picked bass.mid')
now=0.
bass_notes=[]
for event in mid:
    now+=event.time
    if event.type=='note_on' and event.velocity:
        bass_notes.append((now,event.note))
for name in ('chorus','chorus2'):
    start=reports[name]['start_s']
    chosen=[(t,p) for t,p in bass_notes if start<=t+.02<start+5.6]
    measured=[]
    for t,pitch in chosen:
        x=bass[round((t+.08)*rate):round((t+.30)*rate)].mean(axis=1)
        response=abs(np.fft.rfft(x*np.hanning(len(x)),65536))
        hz=np.arange(len(response))*rate/65536
        target=440*2**((pitch-69)/12)
        range_mask=(hz>=target*.86)&(hz<=target*1.16)
        selected=hz[range_mask][np.argmax(response[range_mask])]
        measured.append(round(float(1200*np.log2(selected/target)),1))
    reports[name]['bass_target_offset_cents']=measured
    assert len(measured)>5 and max(abs(v) for v in measured)<35
(here/'rendered-review.json').write_text(json.dumps(reports,indent=2)+'\n')

def spectrogram(data,start,end):
    crop=data[round(rate*start):round(rate*end)].mean(axis=1)
    f,t,q=signal.stft(crop,fs=rate,nperseg=2048,noverlap=1792)
    select=(f>=42)&(f<=8800)
    return f[select],t+start,db(abs(q[select])**2)

def beat_lines(ax, start, end):
    for t in np.arange(np.ceil(start/beat)*beat,end,beat):
        ax.axvline(t,alpha=.20,color='white',linewidth=.45)
    for s in sections:
        if start<=s['start']<end:
            ax.axvline(s['start'],alpha=.70,color='grey',linewidth=1)

for start,end,name in [(76.,95.,'first-chorus'),(141.,172.,'last-chorus')]:
    fig,axes=plt.subplots(4,1,figsize=(11,8.6),sharex=True,constrained_layout=True)
    lo,hi=round(start*rate),round(end*rate)
    scale=np.sqrt(np.mean(mix[lo:hi]**2)/np.mean(old[lo:hi]**2))
    for ax, data, label in zip(axes[:2], (old*scale,mix), ('Published mix at matched RMS','New REAPER render')):
        f,t,mag=spectrogram(data,start,end)
        ax.pcolormesh(t,f,mag,vmin=-78,vmax=-22,shading='auto',cmap='magma')
        ax.set(yscale='log',ylabel='Hz',title=label)
        beat_lines(ax,start,end)
    for data,label in [(band_voice,'Lead, 900–3800 Hz'),(band_back,'Backing, 900–3800 Hz'),(drum_low,'Drums, 37–130 Hz')]:
        power=framed(data[lo:hi],peak_frame)
        axes[2].plot(start+(np.arange(len(power))+.5)*peak_frame/rate,db(power),label=label)
    axes[2].set(ylim=(-64,-11),ylabel='dBFS')
    axes[2].legend(loc='lower right',fontsize=8)
    # Check the new harmony with the predominantly monophonic bass.
    sample=bass[lo:hi].mean(axis=1)
    hop=256
    cqt=abs(librosa.cqt(sample,sr=rate,hop_length=hop,
                       fmin=librosa.midi_to_hz(28),n_bins=38))
    axes[3].pcolormesh(start+np.arange(cqt.shape[1])*hop/rate,np.arange(28,66),db(cqt*cqt),
                       cmap='magma',vmin=-62,vmax=-7,shading='auto')
    axes[3].scatter([t for t,p in bass_notes if start<t<end],
                    [p for t,p in bass_notes if start<t<end],s=8,c='cyan',label='Bass MIDI attacks')
    axes[3].set(xlim=(start,end),ylim=(28,64),ylabel='MIDI pitch',xlabel='Song time (s)')
    axes[3].legend(loc='upper right',fontsize=8)
    for ax in axes[2:]:
        beat_lines(ax,start,end)
    fig.savefig(here/(name+'.png'),dpi=135)
    plt.close(fig)
print(json.dumps(reports,indent=2))
