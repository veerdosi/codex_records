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
  iFreq = cpsmidinn(p4)
  aAmp linseg 0,.0036,1,.029,.65,p3-.0326,0
  kCut expon 5100,p3,980
  aPulse vco2 .51,iFreq,2,.28
  aOctave vco2 .18,iFreq*2,12
  aBody moogladder aPulse+aOctave,kCut,.16
  aBloom oscili .19,iFreq,1
  aSignal atone (aBody+aBloom)*aAmp*p5*3.65,180
  outs aSignal*sqrt(1-p6),aSignal*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0.006000 0.113000 71 0.185000 0.370000
i 1 0.010000 0.091000 64 0.098000 0.480000
i 1 0.176000 0.136000 76 0.178000 0.610000
i 1 0.179000 0.108000 71 0.080000 0.500000
f 0 0.339853658537
e
</CsScore>
