"""Check the balance on the rendered mixes and audit source/arrangement timing."""
from pathlib import Path
import json

import numpy as np
from scipy import signal
import soundfile as sf

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
SONG = ANALYSIS.parent
ROOT = SONG.parents[2]
MEDIA = ROOT/'reaper/Sunn Raha Hai (Under Glass)/Media'
R = 44100
SCORE = json.loads((ANALYSIS/'arrangement.json').read_text())
BEAT = 60/SCORE['bpm']
BANDS = (140,5700)
HOP = 2205


def read(path):
    data, rate = sf.read(path,dtype='float32',always_2d=True)
    assert rate==R and np.isfinite(data).all(),path
    return data


def band(x, frequencies):
    sos = signal.butter(2,frequencies,btype='bandpass',fs=R,output='sos')
    return signal.sosfilt(sos,x,axis=0)


def crop(x,a,b):
    return x[round(a*R):round(b*R)]


def db(x):
    return 10*np.log10(max(1e-12,np.mean(x*x)))


def frames(x):
    return np.mean(x[:len(x)//HOP*HOP].reshape(-1,HOP,2)**2,axis=(1,2))


def balances(name, before_back, before_mix, drum_name):
    old = ANALYSIS/'dream_pop'
    old_back, old_mix, new_back, new_mix = [read(path) for path in
        (old/before_back,old/before_mix,HERE/f'{name} Backing.wav',HERE/f'{name} Premaster.wav')]
    assert new_mix.shape==old_mix.shape==new_back.shape==old_back.shape
    assert np.max(np.abs(new_mix))<.9999
    raw_old_voice, raw_new_voice = old_mix-old_back, new_mix-new_back
    ov,nv,ob,nb = [band(x,BANDS) for x in (raw_old_voice,raw_new_voice,old_back,new_back)]

    # Fix the comparison mask to the original vocal activity.
    movements=[]
    for part in SCORE['sections']:
        a,b,where=part['start'],part['end'],part['name']
        active = frames(crop(ov,a,b)) > .0005
        if not active.any():
            continue
        levels=[frames(crop(x,a,b))[active].mean() for x in (ov,nv,ob,nb)]
        old_margin = 10*np.log10(levels[0]/levels[2])
        new_margin = 10*np.log10(levels[1]/levels[3])
        if where not in ('guitar intro', 'guitar interlude'):
            assert 1.9 <= old_margin-new_margin <= 7.5,(where,old_margin,new_margin)
        movements.append((where,round(float(old_margin),1),round(float(new_margin),1)))

    # Locate the corresponding pickup and vocal syllables in both renders.
    # The search also catches an accidental clip offset from file/FX changes.
    vocal_lags=[]
    for t in (11.19,40.84,50.12,83.65,102.40,119.07,143.31,149.69,160.74,169.58):
        a=round(t*R)
        count=round(.23*R)
        search=round(.055*R)
        reference=ov[a:a+count].mean(axis=1)
        nearby=nv[a-search:a+count+search].mean(axis=1)
        if not float(np.max(np.abs(reference)))>.02:
            continue
        correlation=signal.correlate(nearby,reference,mode='valid',method='fft')
        sums=np.r_[0.,np.cumsum(nearby**2,dtype=np.float64)]
        denom=np.sqrt(np.maximum(sums[count:]-sums[:-count],1e-10)*np.sum(reference**2))
        peak=int(np.argmax(correlation/denom))
        lag=(peak-search)*1000/R
        assert abs(lag)<=.15 and (correlation/denom)[peak]>.999,(t,lag)
        vocal_lags.append(round(lag,3))

    # Verify that the earlier parts of the refrain swells gained emphasis
    # relative to each version's new backing level.
    swell=[]
    for t,peak in ((84.28939358464,83.72),(150.31608522594,149.79)):
        x,y=[band(crop(p,t-1.0,t+1.0),[340,2200]) for p in (old_back,new_back)]
        i=peak-(t-1)
        window=(i-.07,i+.10)
        before_difference=db(crop(x,*window))-db(crop(x,.15,.35))
        after_difference=db(crop(y,*window))-db(crop(y,.15,.35))
        swell.append({'time':peak,'relative_presence_change_db':round(float(after_difference-before_difference),2)})

    check = (102.44,102.54)
    before_echo = band(read(HERE/f'{name} Backing.before-echo.wav'),BANDS)
    echo_level_before,echo_level_after = [db(crop(x,*check)) for x in (before_echo,nb)]
    assert echo_level_after>echo_level_before
    delta = new_back-read(HERE/f'{name} Backing.before-echo.wav')
    assert max(np.max(np.abs(delta[:round(102.28*R)])),
               np.max(np.abs(delta[round(102.82*R):]))) < 2e-6

    drum = band(read(MEDIA/f'{drum_name}.wav').mean(axis=1),[36,122])
    offsets=[]
    for part in SCORE['sections']:
        if part['name'] not in ('chorus','chorus2'):
            continue
        for start in np.arange(part['start'],part['end']-.1,4*BEAT):
            a=round((start-.040)*R)
            b=round((start+.070)*R)
            rms=np.convolve(drum[a:b]**2,np.ones(132)/132,mode='same')
            k=int(np.flatnonzero(rms>.18*max(rms))[0])
            assert np.max(rms)>.002
            offsets.append(1000*((a+k)/R-start))
    assert len(offsets)==12
    assert max(abs(np.asarray(offsets)))<32,offsets

    return dict(vocal_over_backing_db=movements,
                max_change_in_vocal_timing_ms=max(map(abs,vocal_lags)),
                chorus_kick_max_offset_ms=round(float(max(abs(np.asarray(offsets)))),2),
                pickup_swells=swell,
                verse_two_pickup_backing_db=[round(float(x),2) for x in (echo_level_before,echo_level_after)],
                premaster_peak_dbfs=round(float(20*np.log10(np.max(np.abs(new_mix)))),2))


source_bars = np.load(ANALYSIS/'source-beats.npz')['bars']
source_errors_ms = []
for part in SCORE['sections']:
    if part['source'] is None or part['name']=='outro':
        continue
    mapped=np.arange(part['source'],part['source']+part['end']-part['start']-.035,4*BEAT)
    source_errors_ms.extend(1000*np.min(abs(source_bars-t)) for t in mapped)
assert max(source_errors_ms)<25
print(json.dumps(dict(max_source_downbeat_grid_error_ms=round(float(max(source_errors_ms)),2),
    shoegaze=balances('Shoegaze','Shoegaze backing.wav','Shoegaze premaster.wav','Live kit'),
    dream_pop=balances('Dream pop','Backing.wav','Premaster.wav','Broken drums')),indent=2))
