<CsoundSynthesizer>
<CsOptions>
-d -m0 -W -3
</CsOptions>
<CsInstruments>
sr = 48000
ksmps = 16
nchnls = 2
0dbfs = 1

instr 1
    aShape linseg 0, .008, p5, .100, p5*.66, p3-.158, p5*.33, .05, 0
    aRoot poscil .88, p4
    aOctave poscil .24, p4*2
    aFifth poscil .07, p4*3
    aBass = tanh((aRoot+aOctave+aFifth)*1.4) * aShape
    aDark tone aBass, 580
    outs aDark, aDark
endin
</CsInstruments>
<CsScore>
i 1 .025 .550 43.654 .70
i 1 .957 .240 51.913 .37
i 1 1.253 .478 43.654 .62
i 1 1.895 .500 43.654 .69
f 0 2.58
e
</CsScore>
</CsoundSynthesizer>
