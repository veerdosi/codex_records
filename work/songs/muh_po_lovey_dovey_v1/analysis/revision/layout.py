"""New 80 BPM arrangement; phrase boundaries use each source's native bar phase."""
from pathlib import Path
import json
p=Path(__file__).resolve().parent
F=90/80
bar=3
T=[
    ['Farebi | Drums','#AD554D',-7.8],['Farebi | Bass','#A46D53',-8.4],
    ['Farebi | Music','#B7876C',-7.1],['Chaar Diwaari | Chorus','#A471A0',-9.1],
    ['Encore ABJ | Verse','#478597',-3.95],['Calm | Verse','#4C9DA2',-5.25],
    ['Veer | Plucks','#687852',-1.0],['Veer | Filtered pulse','#7E8F60',-4.0],['Veer | Metal ticks','#77838E',2.0],
]
files=['Farebi - drums.wav','Farebi - bass.wav','Farebi - music.wav','Farebi - chorus.wav']
I=[]
def clip(t,src,pos,dur,db=0,fi=.008,fo=.035,file=None):
    assert pos>=0 and src>=0 and dur>0
    I.append([t,file or files[t],src,dur,pos,db,fi,fo])
def bed(src,dst,bars,levels=(0,0,0),fi=0,tail=.035):
    for t,db in enumerate(levels):
        if db is not None:
            clip(t,src*bar+.008*F,dst*bar,bars*bar,db,max(fi,[.005,.013,.048][t]),max(tail,[.035,.050,.076][t]))
def hook(dst,anchor,start,end,db):
    clip(3,start*F,dst*bar+(start-(anchor*240/90+.008))*F,(end-start)*F,db,.011,.067)
def rap(t,dst,anchor,start,end,db=0):
    clip(t,start,dst*bar+start-anchor,end-start,db,.011,.027,'Namastute - native vocals.wav')
def extra(t,src,pos,dur,db=0,fi=.025,fo=.10):
    clip(t,src,pos,dur,db,fi,fo,f'Veer - harmony {t-5}.wav')
# A one-bar cold open uses the existing pickup. The full arrangement
# begins on its next downbeat, with no new rhythmic layer before it.
clip(6,0,9,1.40,0,.02,.06,'Veer - vocal room.wav')
bed(19,4,18)
hook(4,19,49.27,71.59,-.10)
# At 48s the instrumental has already been going for four bars without a lead vocal.
rap(4,16,6.322,6.23,60.625)
bed(3,22,8,(-.3,-.2,-.6))
# Farebi's second pre-chorus material opens under Encore, then resolves into its chorus.
bed(46,30,14,(0,-.1,-.05))
for t,db in [(6,-3.8),(8,-4.5)]: extra(t,12,103.5,2.90,db,.018,.12)
hook(36,52,137.28,159.53,-.1)
# Put the drums and bass from the first post-chorus back under the second handoff.
# Let the brass entrance at 144 lead Calm's first complete phrase.
bed(27,44,6,(-.2,-.3,-.65))
rap(5,48,60.322,60.625,102.073)
clip(5,0,144+102.073-60.322,102.267-102.073,0,.009,.020,
     'Calm - falling syllable.wav')
bed(6,50,8,(-.2,-.1,-.5))
bed(72,58,6,(-.25,-.2,-.35))
# The keys answer the chord just before the sung pickup.
clip(6,0,189.1875,1.15,1.0,.012,.10,'Veer - pickup keys.wav')
# Carry the last chord and a little percussion under the sung pickup.
clip(2,0,190.445,1.71,1.2,.018,.14,'Farebi - pickup chord tail.wav')
clip(0,64.509,190.5,1.5,-10.2,.065,.053)
# Use the complete clean answer from the first chorus in place of the ad-lib
# and its residual vowel. Resume at the breath before the next phrase.
hook(64,78,206.699,210.53,-.85)
clean_start, clean_end = 50.592, 51.763
clean_position = 192 + (clean_start + 162.62 - 208.008)*F
clip(3,clean_start*F,clean_position,(clean_end-clean_start)*F,-.85,.012,.053)
hook(64,78,214.527,234.667,-.85)
bed(78,64,10,(0,-.2,None))
clip(2,234.009,192,2.855,0,.048,.045)
clip(6,0,194.806,3.868,1.7,.019,.096,'Veer - chorus reply.wav')
clip(2,240.626,198.617,23.383,0,.092,.076)
# Some of the prior pocket carries through the four bars where the original thins out.
bed(19,64,3.95,(-7.1,-7.4,None),.07,.18)
# Brief coda in the final Farebi sound, with a short original rhythmic callback.
bed(54,74,1,(-4.8,-3.4,-1.0),.06,.19)
bed(55,75,1,(None,-6.2,-2.2),.035,.9)
for t,gain in [(6,-3.5),(7,-7),(8,-5)]:extra(t,15,222,3.78,gain,.016,.48)
R=[
    (3,4,'Intro | Vocal pickup'),
    (4,12,'Chaar Diwaari | Chorus I'),(12,16,'Farebi | Post-chorus groove'),
    (16,34,'Encore ABJ | Original cadence'),(34,36,'Instrumental turnaround'),
    (36,44,'Chaar Diwaari | Chorus II'),(44,48,'Farebi | Drum and brass lead-in'),
    (48,62,'Calm | Brass entrance'),(62,64,'Instrumental turnaround'),
    (64,74,'Chaar Diwaari | Final chorus'),(74,76,'Coda')
]
offset=9
for item in I:
    item[4] -= offset
envelopes={
    1: [[0,0],[186,0],[187.75,-.5],[188.65,-3.4],[189.32,-1.4],
        [190.1,-2.4],[190.52,-8],[191.6,-8],[192,0],[228,0]],
    3: [[0,0],[189,0],[190,-1.2],[197.25,-1.2],[197.45,-1.9],
        [203.6,-1.9],[204.36,.85],[228,.85]],
}
# Zero out the previous intro's automation and retain the balance moves
# elsewhere in the song at their new positions.
envelopes[0]=[[0,0],[228,0]]
envelopes[2]=[[0,0],[228,0]]
for points in envelopes.values():
    for point in points:
        point[0]=max(0,point[0]-offset)
(p/'arrangement.json').write_text(json.dumps(dict(
    duration=228-offset,artist='Seedhe Maut, Chaar Diwaari, Raftaar & Veer',
    tracks=T,items=I,envelopes=envelopes,
    regions=[(a*bar-offset,b*bar-offset,n) for a,b,n in R]),indent=2))
