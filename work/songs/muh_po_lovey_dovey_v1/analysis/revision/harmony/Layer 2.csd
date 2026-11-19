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
i 2 0.013000 0.480000 52 0.105000 0.4900
i 2 0.757000 0.260000 59 0.080000 0.4900
i 2 1.882000 0.260000 52 0.096000 0.4900
i 2 2.265000 0.210000 59 0.077000 0.4900
i 2 3.003000 0.270000 47 0.099000 0.4900
i 2 3.753000 0.280000 47 0.085000 0.4900
i 2 4.500000 0.420000 47 0.090000 0.4900
i 2 5.250000 0.380000 47 0.083000 0.4900
i 2 6.003000 0.300000 52 0.107000 0.4900
i 2 6.756000 0.240000 52 0.088000 0.4900
i 2 7.878000 0.240000 52 0.095000 0.4900
i 2 8.254000 0.240000 59 0.081000 0.4900
i 2 15.030000 0.220000 55 0.060000 0.4900
i 2 16.546000 0.300000 54 0.058000 0.4900
f 0 18.8
e
</CsScore>
</CsoundSynthesizer>
