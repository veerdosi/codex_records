"""Original synth rhythm for the intro and turnarounds at 80 BPM."""
from pathlib import Path
import sys,subprocess
import numpy as np,soundfile as sf
from pedalboard import Pedalboard, Reverb
p=Path(__file__).parent
media=Path(sys.argv[1])
beat=.75
orc='''<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=32
nchnls=2
0dbfs=1
instr 1
  ifreq=cpsmidinn(p4)
  aenv linseg 0,.005,1,p3*.34,.45,p3*.35,.12,p3*.31-.005,0
  kindex expon p7,p3,.19
  adet foscil p5*aenv,ifreq*1.0019,1,2.005,kindex,1
  amain foscil p5*aenv,ifreq,1,2,kindex,1
  atone tone amain+adet*.31,4800
  outs atone*sqrt(1-p6),atone*sqrt(p6)
endin
instr 2
  ifreq=cpsmidinn(p4)
  aenv linseg 0,.022,.82,p3*.19,.95,p3*.47,.5,p3*.34-.022,0
  klfo oscili 250,1.7,1
  atone1 vco2 p5,ifreq,12
  atone2 vco2 p5*.35,ifreq*1.005,12
  aleft moogladder atone1,680+klfo,.22
  aright moogladder atone2+atone1*.72,810-klfo,.25
  outs aleft*aenv*sqrt(1-p6),aright*aenv*sqrt(p6)
endin
instr 3
  aenv expon 1,p3,.001
  ar noise p5*aenv,0
  az butterbp ar,p4,p4*.6
  kidx expon 2.1,p3,.1
  am foscil p5*aenv*.16,p4*.56,1,1.414,kidx,1
  outs (az+am)*sqrt(1-p6),(az+am)*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
'''
# Each bar keeps its own syncopation, voicing and register. E pedal under i, VI, iv, V.
events=[]
def n(i,t,d,pitch,gain,pan=.5,index=1.2):
    events.append((i,t,d,pitch,gain,pan,index))
voicings=[(52,59,67,71,78),(52,60,67,71,76),(52,57,64,67,72),(47,57,63,66,74)]
for j,notes in enumerate(voicings):
    start=4*j
    chord=notes[:4]
    rhythm=[[(0,.36),(.75,.20),(1.50,.31),(2.75,.34)],
            [(0,.40),(1.25,.26),(2.25,.23),(3.50,.36)],
            [(0,.38),(.50,.23),(1.75,.29),(2.50,.37),(3.25,.23)],
            [(0,.58),(.75,.24),(1.50,.28),(2.25,.30)]][j]
    for k,(t,d) in enumerate(rhythm):
        for m,key in enumerate(chord[(k%2):]):
            n(1,start+t+m*.013,d,key,.035 if m==0 else .027,.22+m*.18,1.2+(k+j)%3*.37)
    for k,t in enumerate((.25,1.12,1.90,2.61,3.16,3.67) if j<3 else (.22,1.11,1.69,2.31)):
        key=notes[3 if (k+j)%3==0 else 4]-(12 if k%4==3 else 0)
        n(1,start+t,.17+k%3*.024,key,.026,.20 if k%2 else .80,1.58)
    n(2,start+.035,3.48 if j<3 else 2.73,notes[0]-12,.10,.52)
    n(2,start+.30,2.10,notes[1],.042,.41)
    for k,t in enumerate((.51,1.22,2.01,2.51,3.25,3.52,3.76) if j<3 else (.51,1.26,2.0,2.56,2.82)):
        n(3,start+t,.08+k%3*.032,4600 if k%3==0 else 7600,.025 if k%3==0 else .018,.28 if k%2 else .66)
for j,base in enumerate((0,4,8,12)):
    for k,off in enumerate((.39,.79,1.04,1.64,2.13,2.39,3.16) if j<3 else (.49,1.2,1.49,2.16)):
        n(1,base+off,.21,[64,71,67,66,72,67,63][(k+j*2)%7],.021,.8 if (k+j)%2 else .2,2.5)
# The two small replies reuse the opening's rhythm but thin the voicing.
for base in (16,20):
    for k,(off,pitch) in enumerate([(0,52),(.74,59),(1.49,64),(1.86,67),(2.48,66),(3.05,63)]):
        n(1,base+off,.33,pitch,.040 if k in (0,2) else .032,.27 if k%2 else .72,1.64)
    n(2,base+.06,2.54,47,.072,.51)
    for off in [1.69,2.25,2.5,2.75,3.12,3.43]:
        n(3,base+off,.091,6900,.029,.57)
for i in (1,2,3):
    score=''.join(f'i {i} {t*beat:.5f} {d*beat:.5f} {note} {g} {pan} {idx}\n' for j,t,d,note,g,pan,idx in events if i==j)
    file=p/f'Intro layer {i}.csd'
    file.write_text(orc+score+'f 0 18.8\ne\n</CsScore>\n</CsoundSynthesizer>\n')
    wav=media/f'Veer - layer {i}.wav'
    subprocess.run(['csound','-o',str(wav),str(file)],check=True)
    x,s=sf.read(wav,dtype='float32')
    x=Pedalboard([Reverb(room_size=.26,damping=.68,wet_level=.13,dry_level=.90,width=.93)])(x.T,s).T
    sf.write(wav,x*(.60 if i==2 else .79),s,subtype='PCM_24')
