"""Arrange Farebi as the continuous palette, with a shared 84 BPM meter."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
B=240/84
F=90/84
N=80/84
f0=.008
n0=.322
T=[
    ['Farebi | Drums','#AD554D',-9.1],['Farebi | Bass','#A46D53',-9.4],
    ['Farebi | Music','#B7876C',-8.8],['Chaar Diwaari | Chorus','#A471A0',-7.7],
    ['Encore ABJ | Verse','#478597',-3.1],['Calm | Verse','#4C9DA2',-4.1],
    ['Veer | Upright','#687852',-12],['Veer | Nylon','#7E8F60',-12.6],['Veer | FM','#77838E',-11],
]
files=['Farebi - drum kit.wav','Farebi - bass.wav','Farebi - production.wav','Farebi - hook lead.wav']
items=[]
def put(t,src,pos,length,db=0,fi=.008,fo=.035,file=None):
    assert pos>=0 and src>=0 and length>0,(t,src,pos,length)
    items.append([t,file or files[t],src,length,pos,db,fi,fo])
def f(t,source_bar,dest_bar,bars,db=0,fi=.008,fo=.035,offset=0):
    put(t,(f0+source_bar*240/90)*F+offset,dest_bar*B+offset,bars*B,db,fi,fo)
def bed(s,d,b,levels=(0,0,0)):
    for t,l in enumerate(levels):
        if l is not None: f(t,s,d,b,l,.008 if t<2 else .042,.036 if t<2 else .13)
def hook(d,s=19,bars=8,mode=0):
    # A two-beat lyrical pickup is kept, with the accompaniment entering at the bar.
    levels=[(0,0,0),(-.15,-.6,-.4),(.1,-.2,.15)][mode]
    bed(s,d,bars,levels)
    a=f0+s*240/90
    if s==19:
        begin,end=49.27,71.60
    else:
        begin,end=206.385,234.667
    put(3,begin*F,d*B+(begin-a)*F,(end-begin)*F,(-.15,0,-.30)[mode],.014,.070)
    # Blend the source harmony into the last beat of the preceding section.
    put(2,(a-1.14)*F,d*B-1.14*F,1.16*F,-3.8,.25,.03)
def rap(track,bar,anchor,begin,end,db=0):
    put(track,begin*N,bar*B+(begin-anchor)*N,(end-begin)*N,db,.009,.021,
        file='Namastute - performance.wav')
# Intro: original score works over Farebi's quiet E pedal; the recorded drum kit
# arrives in layers. The hook pickup has a clear lane of its own.
f(2,60,0,2,-4,.09,.22); f(1,60,0,2,-4.5,.36,.28)
f(2,3,2,1.58,-8,.24,.37); f(0,3,2,1.54,-5.0,.22,.22)
f(1,3,2,1.50,-4.8,.2,.18)
hook(4)
# Encore: build from the first Farebi groove, then open up the second half.
bed(3,12,8,(-1.25,-.8,-2.15))
bed(36,20,8,(-.75,-.55,-2.1))
bed(3,28,2,(-1.1,-.8,-1.4))
f(2,61,30,1,-2.4,.13,.32)
f(0,3,30,.50,-4,.022,.16)
rap(4,12,6+n0,6.23,60.625,.1)
hook(31,mode=1)
# The two-bar hinge lets the full refrain end before Calm arrives.
f(2,60,39,2,-3.0,.12,.26); f(1,60,39,2,-4.2,.18,.30)
f(0,24,40.5,.5,-3.4,.032,.038,offset=0)
# Calm: a tighter, drier pocket, then a busier arrangement as the verse winds up.
bed(27,41,8,(-.45,-.5,-1.7))
bed(44,49,8,(-1.0,-.45,-2.3))
rap(5,41,60+n0,60.625,109.02,.1)
f(2,62,57,1,-2.7,.18,.3)
f(1,62,57,.65,-4.5,.09,.21)
hook(58,s=78,bars=10,mode=2)
f(0,19,58,3.94,-9.5,.04,.22)
f(1,19,58,3.86,-10.2,.12,.31)
# Outro: Farebi's sparse breakdown, with short nylon phrases brought back as a reply.
f(2,60,68,6,.2,.06,1.1); f(1,60,68,2,-.6,.09,1.1)
put(2,0,68*B-.12,3.2,5.8,.035,.32,'Farebi - chord tail.wav')
f(0,60,68,2,-.6,.05,.72)
for t,file in [(6,'Upright - frame.wav'),(7,'Nylon - answer.wav'),(8,'FM - room.wav')]:
    put(t,0,0,3.68*B,(0,1,0)[t-6],.012,.23,file)
    put(t,38*B,39*B,2*B,-4,.07,.26,file)
    if t!=6:
        put(t,64*B,68*B,5.98*B,-3.0 if t==7 else -6.0,.15,.82,file)
regions=[
    (0,4,'Intro | Original motif over Farebi'),(4,12,'Chaar Diwaari | Chorus I'),
    (12,30,'Encore ABJ | Namastute'),(30,31,'Turnaround'),
    (31,39,'Chaar Diwaari | Chorus II'),(39,41,'Bridge | Guitar answer'),
    (41,57,'Calm | Namastute'),(57,58,'Turnaround'),
    (58,68,'Chaar Diwaari | Final chorus'),(68,74,'Outro | Farebi and nylon')
]
(p/'arrangement.json').write_text(json.dumps(dict(duration=74*B,artist='Seedhe Maut, Chaar Diwaari, Raftaar & Veer',
    tracks=T,items=items,regions=[(a*B,b*B,n) for a,b,n in regions]),indent=2))
