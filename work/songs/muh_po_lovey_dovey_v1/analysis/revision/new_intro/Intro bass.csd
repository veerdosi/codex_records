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
  iHz = cpsmidinn(p4)
  aEnv linseg 0,.006,1,.064,.75,p3-.07,0
  aRoot oscili p5*aEnv,iHz,1
  aSecond oscili .34*p5*aEnv,iHz*2,1
  aThird oscili .12*p5*aEnv,iHz*3,1
  aVoice tone aRoot+aSecond+aThird,550
  outs aVoice,aVoice
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0.00000 0.85500 40 0.13
i 1 1.12500 0.26250 40 0.094
i 1 1.50000 0.58500 40 0.12
i 1 2.62500 0.24000 43 0.087
i 1 3.00000 0.81000 36 0.125
i 1 4.12500 0.23250 36 0.092
i 1 4.50000 0.69000 36 0.121
i 1 5.62500 0.23250 38 0.093
i 1 6.00000 0.79500 40 0.128
i 1 7.12500 0.25500 40 0.097
i 1 7.50000 0.77250 45 0.117
i 1 8.62500 0.21000 45 0.081
i 1 9.00000 0.75750 35 0.126
i 1 10.12500 0.24750 35 0.093
f 0 12
e
</CsScore>
</CsoundSynthesizer>
