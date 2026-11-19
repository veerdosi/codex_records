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
i 3 1.688000 0.058000 5400 0.031000 0.6100
i 3 2.442000 0.061000 6400 0.028000 0.3700
i 3 3.935000 0.056000 5200 0.026000 0.6100
i 3 5.440000 0.064000 6100 0.028000 0.3900
i 3 7.688000 0.058000 5600 0.030000 0.6100
i 3 8.452000 0.062000 6800 0.027000 0.3700
f 0 9.04
e
</CsScore>
</CsoundSynthesizer>
