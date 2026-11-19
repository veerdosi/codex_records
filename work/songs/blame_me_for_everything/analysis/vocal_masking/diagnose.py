"""Measure the vocal's spectral balance and the sounds competing with it."""
import sys
from pathlib import Path

import numpy as np
from scipy.signal import welch, sosfiltfilt, butter
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'first_hook_exit'))
import measure

measure.START = 65
measure.END = 108
PROJECT = measure.PROJECT
RATE = measure.RATE
rpp = PROJECT / 'Blame Me for Everything.rpp'
tracks = measure.read_tracks(rpp)
savage = next(y for name, y in tracks.items() if name.startswith('21 Savage |'))
kanye = next(y for name, y in tracks.items() if name.startswith('Kanye West |'))
backing = sum(y for name, y in tracks.items() if not measure.is_vocal(name))
main_bed = tracks['Runaway | Instrumental']
bands = [(130,300),(300,700),(700,1400),(1400,2200),(2200,4500),(4500,8000),(8000,12000)]
BLOCK = 2205


def block_db(x, a, b):
    sos = butter(2, [a, b], fs=RATE, btype='bandpass', output='sos')
    y = sosfiltfilt(sos, x, axis=0)
    return 10*np.log10(np.maximum(1e-12, (y.reshape(-1,BLOCK,2)**2).mean((1,2))))


def difference(vocal, music):
    activity = block_db(vocal,190,6200)
    valid = activity > np.percentile(activity, 80) - 11
    result = []
    for a, b in bands:
        v, m = block_db(vocal,a,b),block_db(music,a,b)
        result.append([round(np.median(v[valid]-m[valid]),2),round(float(np.mean(v[valid]<m[valid])*100),1)])
    return result


if __name__ == '__main__':
    for name, a, b, voice in [('Savage early',66.25,74.25,savage), ('Savage middle',74.25,86.25,savage),
                              ('Savage late',86.25,95.75,savage),('Kanye return',102.25,107.75,kanye)]:
        sl = slice(measure.sample(a-65),measure.sample(b-65))
        print(name, 'median vocal over backing dB and % of vocal-active windows below backing')
        for (lo,hi), (db,pct) in zip(bands,difference(voice[sl],backing[sl])):
            print(f'  {lo:4}–{hi:5} {db:+6.2f} dB {pct:5.1f}%')
        for title, x in [('Bed',main_bed), *tracks.items()]:
            if title=='Runaway | Instrumental' or measure.is_vocal(title):
                continue
            y = x[sl]
            p=measure.rms(y)
            if p>-53:
                z = block_db(y,1900,5200)
                print(f'    {title:38} RMS {p:6.2f}  presence {10*np.log10(np.mean(10**(z/10))):6.2f}')

    song = HERE.parents[1]
    aligned_at = 124.71125
    with sf.SoundFile(song / 'sources/creepin_album.wav') as source:
        source.seek(measure.sample(aligned_at))
        extract=source.read(measure.sample(30.60),dtype='float32',always_2d=True)
    lead, sr = sf.read(song / 'stems/creepin_album lead.wav',dtype='float32')
    offset=measure.sample(2.515)
    length=(len(lead)-offset-measure.sample(1.45))//BLOCK*BLOCK
    lead=lead[offset:offset+length]
    extract=extract[offset:offset+length]
    print('Original reference',difference(lead,extract-lead))
