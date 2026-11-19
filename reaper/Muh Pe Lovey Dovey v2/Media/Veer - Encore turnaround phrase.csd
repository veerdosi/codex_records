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
i 1 0.080000 0.153000 59 0.205000 0.4300
i 1 0.083000 0.135000 64 0.115000 0.5200
i 1 0.329000 0.151000 71 0.265000 0.5400
i 1 0.501000 0.183000 76 0.350000 0.4700
i 1 0.504000 0.172000 71 0.164000 0.5200
f 0 0.702707317073
e
</CsScore>
