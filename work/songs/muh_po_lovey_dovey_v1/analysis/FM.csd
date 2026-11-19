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
  iF = cpsmidinn(p4)
  aEnv linseg 0,p3*.23,1,p3*.43,.71,p3*.34,0
  kIdx linseg .42,p3*.63,1.07,p3*.37,.2
  aL foscil .075*aEnv,iF,1,2.002,kIdx,1
  aR foscil .075*aEnv,iF*.9989,1,2.004,kIdx,1
  aC oscili .075*aEnv,iF*.5,1
  outs aL+aC,aR+aC
endin
instr 2
  aEnv expon 1,p3,.001
  kIndex expon 4.7,p3,.12
  aHit foscil .047*aEnv,cpsmidinn(p4),1,2.77,kIndex,1
  aTilt tone aHit,2400
  outs aTilt,aTilt*.74
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0.0000000 5.7142857 40
i 1 5.7142857 2.8571429 40
i 1 8.5714286 2.6714286 47
i 1 107.1428571 4.2857143 40
i 1 111.4285714 2.8571429 47
i 1 182.8571429 5.7142857 40
i 1 188.5714286 2.8571429 47
i 1 191.4285714 7.1428571 40
i 2 5.3571429 .4 76
i 2 9.6428571 .4 76
i 2 10.1785714 .4 76
i 2 10.7142857 .4 76
i 2 11.0714286 .4 76
i 2 107.5000000 .4 76
i 2 108.5714286 .4 76
i 2 111.0714286 .4 76
i 2 112.8571429 .4 76
i 2 113.3928571 .4 76
i 2 113.7500000 .4 76
i 2 190.3571429 .4 76
i 2 193.2142857 .4 76
f 0 200
e
</CsScore>
</CsoundSynthesizer>
