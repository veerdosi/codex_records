"""Compare active vocal-to-backing levels and verify the revised handoff."""
from pathlib import Path
import sys
import numpy as np
from scipy.signal import butter, correlate, lfilter, sosfilt
import soundfile as sf

session = Path(sys.argv[1])
rate = 48000


def read(path, start, end):
    with sf.SoundFile(path) as audio:
        assert audio.samplerate == rate
        audio.seek(round(start * rate))
        return audio.read(round((end - start) * rate), dtype='float32')


def stem(name, start, end):
    return read(session / 'Renders/Stems' / f'{name}.wav', start, end)


def backing(start, end):
    return sum(stem('Farebi _ ' + name, start, end) for name in ('Drums', 'Bass', 'Music'))


def active_ratio(lead, bed, speech_band=False):
    def power(audio):
        if speech_band:
            audio = sosfilt(butter(2, [650, 3700], fs=rate, btype='bandpass', output='sos'), audio, axis=0)
        else:
            audio = lfilter([1.53512486,-2.69169619,1.19839281],[1,-1.69065929,.73248077],audio,axis=0)
            audio = lfilter([1,-2,1],[1,-1.99004745,.99007225],audio,axis=0)
        count = len(audio) // 9600
        return (audio[:count * 9600] ** 2).reshape(count, 9600, 2).mean(axis=(1, 2))
    vocal_power, bed_power = power(lead), power(bed)
    active = vocal_power > vocal_power.max() * .045
    return 10 * np.log10(vocal_power[active].sum() / bed_power[active].sum())


for name,start,end in [
    ('Encore ABJ _ Verse',48,99.11),('Calm _ Verse',144.3,185.94),
    ('Chaar Diwaari _ Chorus',12,36),('Chaar Diwaari _ Chorus',108,132),
    ('Chaar Diwaari _ Chorus',192,204),('Chaar Diwaari _ Chorus',204,222),
]:
    lead, bed = stem(name,start,end), backing(start,end)
    ratio = active_ratio(lead,bed)
    print(name,start,end,'broadband',round(ratio,2),'speech band',round(active_ratio(lead,bed,True),2))
    if 'Verse' in name:
        assert abs(ratio - -2.44) < .8, ratio
clean_start, clean_end = 194.845, 197.395
cut = stem('Chaar Diwaari _ Chorus', clean_start, clean_end)
bed = backing(clean_start, clean_end)
assert np.max(np.abs(cut)) < 2e-7
blocks = bed[:len(bed)//12000*12000].reshape(-1,12000,2)
rms = 10*np.log10(np.mean(blocks**2,axis=(1,2)))
assert rms.min()>-44
print('Edited line span',clean_start,clean_end,'chorus stem silent; backing per quarter-second',np.round(rms,1))
for source_start in [60.75, 70, 82, 101]:
    ref = read(session/'Media/Namastute - native vocals.wav',source_start,source_start+.45)[:,0]
    target = 144 + source_start - 60.322
    pad = .004
    found = stem('Calm _ Verse',target-pad,target+.45+pad)[:,0]
    lag = int(np.argmax(correlate(found,ref,mode='valid',method='fft'))) - round(pad*rate)
    assert abs(lag) < 8, lag
    print('Calm source phrase',source_start,'sample offset',lag)
