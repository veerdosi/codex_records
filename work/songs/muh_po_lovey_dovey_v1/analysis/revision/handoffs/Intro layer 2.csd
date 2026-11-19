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
i 2 0.025300 0.300000 47 0.063000 0.5000
i 2 0.749900 0.510000 52 0.067000 0.5000
i 2 1.875800 0.420000 52 0.062000 0.5000
i 2 3.379900 0.280000 55 0.051000 0.5000
i 2 4.504100 0.310000 54 0.049000 0.5000
i 2 5.246300 0.260000 50 0.049000 0.5000
i 2 5.982300 0.500000 52 0.073000 0.5000
i 2 7.503000 0.300000 52 0.057000 0.5000
f 0 9.04
e
</CsScore>
</CsoundSynthesizer>
