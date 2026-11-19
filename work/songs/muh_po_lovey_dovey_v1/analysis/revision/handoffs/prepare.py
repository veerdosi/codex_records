"""Print an intro scored to Farebi's continuous lead-in and a short pickup tail."""
from pathlib import Path
import subprocess
import sys

import numpy as np
from pedalboard import HighpassFilter, Pedalboard, Reverb
from scipy.signal import butter, sosfilt
import soundfile as sf

folder = Path(__file__).resolve().parent
media = Path(sys.argv[1])
rate = 48000
# The drum anchors are taken from Farebi's 45.009s source section. Stagger
# the replies around its bass movement and leave the last pre-chorus bar open.
notes = [
    [
        (.0253,.30,59,.054,.44),(.0253,.25,66,.032,.59),
        (.7499,.28,64,.061,.50),(1.1254,.24,67,.052,.55),
        (1.8758,.26,71,.050,.42),(2.2319,.24,67,.043,.56),
        (2.6238,.20,64,.038,.49),(2.9894,.28,67,.052,.49),
        (3.3799,.22,71,.043,.57),(3.7433,.28,67,.049,.43),
        (4.1309,.22,66,.045,.51),(4.8693,.22,69,.042,.60),
        (5.2463,.26,66,.047,.46),(5.6217,.20,62,.039,.55),
        (5.9823,.36,64,.060,.44),(5.9823,.29,71,.032,.63),
        (6.7563,.27,67,.054,.50),(7.1286,.23,71,.048,.56),
        (7.8791,.26,67,.044,.48),(8.2640,.23,64,.039,.54),
        (8.6260,.20,66,.031,.45),
    ],
    [
        (.0253,.30,47,.063,.5),(.7499,.51,52,.067,.5),
        (1.8758,.42,52,.062,.5),(3.3799,.28,55,.051,.5),
        (4.5041,.31,54,.049,.5),(5.2463,.26,50,.049,.5),
        (5.9823,.50,52,.073,.5),(7.503,.30,52,.057,.5),
    ],
    [
        (1.688,.058,5400,.031,.61),(2.442,.061,6400,.028,.37),
        (3.935,.056,5200,.026,.61),(5.440,.064,6100,.028,.39),
        (7.688,.058,5600,.030,.61),(8.452,.062,6800,.027,.37),
    ],
]
for layer, events in enumerate(notes, 1):
    source = folder.parent / 'harmony' / f'Layer {layer}.csd'
    orchestra = source.read_text().split('<CsScore>\n', 1)[0]
    score = '\n'.join(
        f'i {layer} {time:.6f} {dur:.6f} {pitch} {gain:.6f} {pan:.4f}'
        for time,dur,pitch,gain,pan in events
    )
    csd = folder / f'Intro layer {layer}.csd'
    csd.write_text(orchestra + '<CsScore>\nf 1 0 4096 10 1\n'
                   + score + '\nf 0 9.04\ne\n</CsScore>\n</CsoundSynthesizer>\n')
    path = media / f'Veer - prechorus {layer}.wav'
    subprocess.run(['csound', '-o', str(path), str(csd)], check=True)
    wave, sample_rate = sf.read(path, dtype='float32')
    assert sample_rate == rate
    effects = Pedalboard([
        HighpassFilter(150 if layer == 1 else 55),
        Reverb(room_size=.23,damping=.70,wet_level=.11,dry_level=.92,width=.88),
    ])
    wave = effects(wave.T, rate).T[:9*rate]
    tail_start = round(8.82*rate)
    wave[tail_start:] *= np.linspace(1,0,len(wave)-tail_start)[:,None]
    sf.write(path, wave, rate, subtype='PCM_24')

# Repeat the last real chord in eighth notes so its harmonics carry into the
# vocal pickup. Filter the repeats and taper them into the downbeat.
with sf.SoundFile(media/'Farebi - music.wav') as source:
    source.seek(round((189.994+42.009)*rate))
    chord = source.read(round(.428*rate), dtype='float32')
chord = sosfilt(butter(2,[225,1880],fs=rate,btype='bandpass',output='sos'),chord,axis=0)
edge = np.minimum(1, np.arange(len(chord)) / (.045*rate))
edge *= np.minimum(1, np.arange(len(chord))[::-1] / (.093*rate))
chord *= edge[:,None]
tail = np.zeros((round(1.71*rate),2))
for index,gain in enumerate((.75,.49,.30,.18)):
    start = round(index*.375*rate)
    tail[start:start+len(chord)] += gain * (chord[:,::-1] if index % 2 else chord)
tail *= np.linspace(1,0,len(tail))[:,None]**.62
sf.write(media/'Farebi - pickup chord tail.wav',tail,rate,subtype='PCM_24')

# An original reply to the sung pickup. The first attack is on 195s,
# and the last melodic note releases into the clean vocal response.
reply_notes = [
    (1,.194,.34,59,.052,.42),(1,.194,.30,66,.035,.59),
    (1,.568,.24,71,.041,.57),(1,.944,.25,66,.043,.48),
    (1,1.320,.30,64,.044,.43),(1,1.694,.28,66,.044,.60),
    (1,2.070,.26,71,.047,.52),(1,2.444,.25,66,.039,.46),
    (1,2.820,.25,64,.035,.53),
    (2,.194,.59,47,.062,.50),(2,1.32,.49,47,.049,.5),
    (2,2.444,.57,52,.045,.50),
    (3,.756,.057,5550,.026,.68),(3,1.507,.061,5700,.028,.36),
    (3,2.258,.055,6100,.023,.65),
]
orchestra = (folder/'Intro layer 1.csd').read_text().split('<CsScore>\n',1)[0]
score = '\n'.join(
    f'i {inst} {t:.6f} {dur:.6f} {pitch} {gain:.6f} {pan:.4f}'
    for inst,t,dur,pitch,gain,pan in reply_notes
)
csd = folder/'Chorus reply.csd'
csd.write_text(orchestra + '<CsScore>\nf 1 0 4096 10 1\n'
               + score + '\nf 0 3.89\ne\n</CsScore>\n</CsoundSynthesizer>\n')
path = media/'Veer - chorus reply.wav'
subprocess.run(['csound','-o',str(path),str(csd)],check=True)
wave,sample_rate = sf.read(path,dtype='float32')
assert sample_rate == rate
fx = Pedalboard([
    HighpassFilter(120),
    Reverb(room_size=.30,damping=.72,wet_level=.17,dry_level=.89,width=.88),
])
wave = fx(wave.T,rate).T[:round(3.868*rate)]
fade_start = round(3.10*rate)
wave[fade_start:] *= np.linspace(1,0,len(wave)-fade_start)[:,None]
sf.write(path,wave,rate,subtype='PCM_24')
