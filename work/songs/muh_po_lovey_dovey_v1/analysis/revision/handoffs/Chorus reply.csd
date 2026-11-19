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
i 1 0.194000 0.340000 59 0.052000 0.4200
i 1 0.194000 0.300000 66 0.035000 0.5900
i 1 0.568000 0.240000 71 0.041000 0.5700
i 1 0.944000 0.250000 66 0.043000 0.4800
i 1 1.320000 0.300000 64 0.044000 0.4300
i 1 1.694000 0.280000 66 0.044000 0.6000
i 1 2.070000 0.260000 71 0.047000 0.5200
i 1 2.444000 0.250000 66 0.039000 0.4600
i 1 2.820000 0.250000 64 0.035000 0.5300
i 2 0.194000 0.590000 47 0.062000 0.5000
i 2 1.320000 0.490000 47 0.049000 0.5000
i 2 2.444000 0.570000 52 0.045000 0.5000
i 3 0.756000 0.057000 5550 0.026000 0.6800
i 3 1.507000 0.061000 5700 0.028000 0.3600
i 3 2.258000 0.055000 6100 0.023000 0.6500
f 0 3.89
e
</CsScore>
</CsoundSynthesizer>
