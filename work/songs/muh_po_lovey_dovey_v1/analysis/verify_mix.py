from pathlib import Path
import json, sys, numpy as np, soundfile as sf
from scipy.signal import lfilter, sosfilt, butter, resample_poly
S=48000
s=Path(sys.argv[1])
conf=json.loads((Path(__file__).parent/'arrangement.json').read_text())
drum,bass,music,hook,encore,calm,piano,nylon,fm=[
    sf.read(s/'Stems'/(t[0].replace('|','_')+'.wav'),dtype='float32')[0] for t in conf['tracks']]
x,sr=sf.read(s/'Premaster.wav',dtype='float32')
assert sr==S
total=drum+bass+music+hook+encore+calm+piano+nylon+fm
assert all(len(t)==len(x) for t in (drum,bass,music,hook,encore,calm,piano,nylon,fm))
to_db=lambda a: 10*np.log10(max(float(a),1e-18))
def lk(t):
    t=lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1.,-1.69065929318241,.73248077421585],t,axis=0)
    t=lfilter([1,-2,1],[1.,-1.99004745483398,.99007225036621],t,axis=0)
    return -.691+to_db(np.mean(np.sum(t*t,axis=1)))
def rms(t): return to_db(np.mean(t*t))
def band(t):
    t=sosfilt(butter(2,[650,3700],btype='bandpass',fs=S,output='sos'),t,axis=0)
    return rms(t)
def seg(t,a,b):return t[round(a*S):round(b*S)]
def peak(t):return to_db(np.max(np.abs(t))**2)
print('duration',len(x)/S,'peak',peak(x),'render-stem sum null',peak(x-total))
bed=drum+bass+music
orig=piano+nylon+fm
voice=hook+encore+calm
for a,b,name in conf['regions']:
    print(name,round(a,2),round(b,2),'mix',round(lk(seg(x,a,b)),1),'bed',round(lk(seg(bed,a,b)),1),
          'voice',round(lk(seg(voice,a,b)),1),'original',round(lk(seg(orig,a,b)),1))
    if 'Chaar' in name or 'Verse' in name or 'Namastute' in name:
        print('   4-bar voice-to-bed | full; 650Hz-3.7kHz')
        for u in np.arange(a,b,240/84*4):
            v=min(b,u+240/84*4)
            if v-u<.1: continue
            v1,b1=seg(voice,u,v),seg(bed+orig,u,v)
            print('  ',round(u,2),round(lk(v1)-lk(b1),1),round(band(v1)-band(b1),1))
print('Intro/outro (mix, Farebi, original, voice) LUFS')
for a in [0,2.857,5.714,8.571,194.286,197.143,200,202.857,205.714,208.571]:
    print(round(a,3),[round(lk(seg(t,a,min(a+2.857,len(x)/S))),1) for t in [x,bed,orig,voice]])
print('Handoff: peak 250ms before; peak after; largest single sample slope nearby')
for a,_,name in conf['regions'][1:]:
    print(name,round(a,3),round(peak(seg(x,a-.25,a)),1),round(peak(seg(x,a,a+.25)),1),
          round(peak(np.diff(seg(x,a-.04,a+.04),axis=0)),1))
