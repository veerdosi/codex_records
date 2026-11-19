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
  iFreq = cpsmidinn(p4)
  aEnv linseg 0,.0055,1,.045,.72,p3-.0505,0
  kIndex expon 1.03,p3,.14
  aCore foscil p5*aEnv,iFreq,1,2,kIndex,1
  aWidth foscil p5*aEnv*.21,iFreq*1.003,1,2.002,kIndex,1
  aTone tone aCore+aWidth,3600
  outs aTone*sqrt(1-p6),aTone*sqrt(p6)
endin
instr 2
  iFreq = cpsmidinn(p4)
  aEnv linseg 0,.006,1,.045,.52,p3-.051,0
  kCut expon 1120,p3,320
  aRaw vco2 p5,iFreq,12
  aPulse moogladder aRaw,kCut,.17
  outs aPulse*aEnv*.73,aPulse*aEnv*.69
endin
instr 3
  aEnv expon 1,p3,.001
  aNoise noise p5*aEnv,0
  aMetal butterbp aNoise,p4,p4*.65
  aRing oscili p5*aEnv*.14,p4*.57,1
  outs (aMetal+aRing)*sqrt(1-p6),(aMetal+aRing)*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0.025300 0.300000 59 0.054000 0.4400
i 1 0.025300 0.250000 66 0.032000 0.5900
i 1 0.749900 0.280000 64 0.061000 0.5000
i 1 1.125400 0.240000 67 0.052000 0.5500
i 1 1.875800 0.260000 71 0.050000 0.4200
i 1 2.231900 0.240000 67 0.043000 0.5600
i 1 2.623800 0.200000 64 0.038000 0.4900
i 1 2.989400 0.280000 67 0.052000 0.4900
i 1 3.379900 0.220000 71 0.043000 0.5700
i 1 3.743300 0.280000 67 0.049000 0.4300
i 1 4.130900 0.220000 66 0.045000 0.5100
i 1 4.869300 0.220000 69 0.042000 0.6000
i 1 5.246300 0.260000 66 0.047000 0.4600
i 1 5.621700 0.200000 62 0.039000 0.5500
i 1 5.982300 0.360000 64 0.060000 0.4400
i 1 5.982300 0.290000 71 0.032000 0.6300
i 1 6.756300 0.270000 67 0.054000 0.5000
i 1 7.128600 0.230000 71 0.048000 0.5600
i 1 7.879100 0.260000 67 0.044000 0.4800
i 1 8.264000 0.230000 64 0.039000 0.5400
i 1 8.626000 0.200000 66 0.031000 0.4500
f 0 9.04
e
</CsScore>
</CsoundSynthesizer>
