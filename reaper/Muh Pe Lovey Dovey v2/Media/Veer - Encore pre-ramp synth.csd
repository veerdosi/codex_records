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
  kCut expon 4200,p3,620
  aPulse vco2 .51,iFreq,2,.28
  aOctave vco2 .18,iFreq*2,12
  aBody moogladder aPulse+aOctave,kCut,.16
  aBloom oscili .19,iFreq,1
  aSignal atone (aBody+aBloom)*aAmp*p5*2.15,180
  outs aSignal*sqrt(1-p6),aSignal*sqrt(p6)
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0.013000 0.105000 64 0.140000 0.310000
i 1 0.022000 0.090000 71 0.072000 0.410000
i 1 0.173000 0.144000 76 0.124000 0.670000
i 1 0.181000 0.111000 71 0.069000 0.580000
f 0 0.33985365853658533
e
</CsScore>
