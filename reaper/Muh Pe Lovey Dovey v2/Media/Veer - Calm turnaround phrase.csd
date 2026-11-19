<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -f
</CsOptions>
<CsInstruments>
sr=48000
ksmps=16
nchnls=2
0dbfs=1
instr 1
  iHz = cpsmidinn(p4)
  aEnv linseg 0,.004,1,.017,.68,p3-.021,0
  kBrightness expon 1.5,p3,.13
  aCore foscil .73*aEnv*p5,iHz,1,2,kBrightness,1
  aOct oscili .12*aEnv*p5,iHz*2,1
  aSoft tone aCore+aOct,4650
  outs aSoft*sqrt(1-p6),aSoft*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0.103000 0.140000 59 0.211000 0.4300
i 1 0.109000 0.125000 64 0.115000 0.5200
i 1 0.332000 0.143000 71 0.265000 0.5600
i 1 0.514000 0.172000 76 0.350000 0.4800
i 1 0.518000 0.166000 71 0.164000 0.5100
f 0 0.702707317073
e
</CsScore>
