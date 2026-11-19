<CsoundSynthesizer>
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
i 2 0.02625 2.61000 40 0.1 0.52 1.2
i 2 0.22500 1.57500 59 0.042 0.41 1.2
i 2 3.02625 2.61000 40 0.1 0.52 1.2
i 2 3.22500 1.57500 60 0.042 0.41 1.2
i 2 6.02625 2.61000 40 0.1 0.52 1.2
i 2 6.22500 1.57500 57 0.042 0.41 1.2
i 2 9.02625 2.04750 35 0.1 0.52 1.2
i 2 9.22500 1.57500 57 0.042 0.41 1.2
i 2 12.04500 1.90500 47 0.072 0.51 1.2
i 2 15.04500 1.90500 47 0.072 0.51 1.2
f 0 18.8
e
</CsScore>
</CsoundSynthesizer>
