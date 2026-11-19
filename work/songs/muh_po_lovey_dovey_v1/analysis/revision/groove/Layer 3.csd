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
  aEnv linseg 0,.0035,1,.026,.64,p3-.0295,0
  kIndex expon 1.82,p3,.19
  aCore foscil p5*aEnv,iFreq,1,2,kIndex,1
  aWidth foscil p5*aEnv*.21,iFreq*1.003,1,2.002,kIndex,1
  aTone tone aCore+aWidth,5200
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
i 3 1.685000 0.063000 5400 0.039000 0.6300
i 3 2.444000 0.063000 7200 0.052000 0.6300
i 3 2.821000 0.063000 7900 0.034000 0.6300
i 3 4.689000 0.063000 5800 0.038000 0.6300
i 3 5.437500 0.063000 6700 0.045000 0.6300
i 3 5.812500 0.063000 7800 0.030000 0.6300
i 3 7.693000 0.063000 5400 0.040000 0.6300
i 3 8.434000 0.063000 6800 0.046000 0.6300
i 3 8.818000 0.063000 7800 0.038000 0.6300
i 3 9.941000 0.063000 7100 0.028000 0.6300
i 3 12.972000 0.063000 5500 0.035000 0.6300
i 3 14.090000 0.063000 7000 0.037000 0.6300
i 3 14.846000 0.063000 7800 0.026000 0.6300
i 3 16.329000 0.063000 6300 0.028000 0.6300
i 3 17.468000 0.063000 7500 0.025000 0.6300
f 0 18.8
e
</CsScore>
</CsoundSynthesizer>
