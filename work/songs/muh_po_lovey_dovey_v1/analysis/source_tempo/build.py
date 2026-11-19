"""Restore native Farebi audio and connect it to the original Namastute cadence."""
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
from subprocess import run
from tempfile import TemporaryDirectory
from uuid import uuid4

import numpy as np
from scipy.signal import butter, correlate, resample_poly, sosfilt
import soundfile as sf

stage = Path(__file__).resolve().parent
root = stage.parents[4]
project = root / 'reaper/Muh Po Lovey Dovey v1'
media = project / 'Media'
generated = stage / 'Media'
generated.mkdir(exist_ok=True)
rate = 48000
definitions = json.loads((stage/'tempo.json').read_text())
bars = [p[0] for p in definitions]
points = [0.]
for (start, bpm, linear), (end, target, _) in zip(definitions, definitions[1:]):
    points.append(points[-1] + (end-start)*80/(.5*(bpm+target) if linear else bpm))

def at(t):
    i = max(0, min(len(bars)-2, bisect_right(bars,t)-1))
    distance = (t-bars[i])*80
    _, bpm, ramp = definitions[i]
    if ramp:
        slope = (definitions[i+1][1]-bpm)/(points[i+1]-points[i])
        return points[i] + 2*distance/(bpm+np.sqrt(bpm*bpm+2*slope*distance))
    return points[i] + distance/bpm

sources = stage.parents[1]/'stems/demucs/htdemucs_ft/farebi'
stems = {'drums':('drums',27),'bass':('bass',29),'music':('other',73),'chorus':('vocals',79)}

def restore(stem):
    source,hp = stems[stem]
    x,sr = sf.read(sources/f'{source}.wav',dtype='float32')
    x = sosfilt(butter(2,hp,fs=sr,btype='highpass',output='sos'),x,axis=0)
    y = resample_poly(x,160,147,axis=0)
    y *= min(1, .999 / np.max(np.abs(y)))
    sf.write(generated/f'Farebi - {stem} at source tempo.wav', y, rate, 'PCM_24')

with ThreadPoolExecutor(4) as pool:
    list(pool.map(restore,stems))

original = (project/(project.name+'.rpp')).read_text()
def field(item, name):
    return re.search(r'^      '+name+r' (.*)$',item,re.M)[1]

def replace(item, name, value):
    return re.sub(r'(?m)^      '+name+r' .*$',lambda _:f'      {name} {value}',item)

def frames(seconds):
    return round(seconds*rate)

def follow_drums(audio, reference, source_time, target_time, length):
    """Use the same waveform alignment on every Farebi backing stem."""
    hop = frames(.018)
    width = hop * 2
    search = frames(.007)
    window = np.hanning(width + 1)[:-1].astype(np.float32)
    centres = np.arange(0,length+hop,hop)
    out = np.zeros((centres[-1]+2*hop,2),dtype=np.float32)
    weight = np.zeros(len(out),dtype=np.float32)
    padded = np.pad(audio,((hop+search+2,hop+search+2),(0,0)))
    mono = np.pad(reference.mean(axis=1),(hop+search+2,hop+search+2))
    pad = hop + search + 2
    prev = None
    for i, centre in enumerate(centres):
        ideal = round(np.interp(centre/rate,target_time,source_time)*rate) + pad
        selected = ideal
        if prev is not None:
            target = mono[prev:prev+hop]
            options = mono[ideal-hop-search:ideal+search]
            energy = np.convolve(options**2,np.ones(hop),mode='valid')
            score = correlate(options,target,mode='valid') / np.sqrt(energy*np.sum(target**2)+1e-12)
            score -= .06*np.square(np.linspace(-1,1,len(score)))
            selected += int(np.argmax(score))-search
        piece = padded[selected-hop:selected+hop]
        first = i*hop
        out[first:first+width] += piece*window[:,None]
        weight[first:first+width] += window
        prev = selected
    return out[hop:hop+length] / np.maximum(weight[hop:hop+length,None],1e-8)

def warp_segment(file, offset, left, right, name):
    # Start before the audible segment so the stretcher arrives with context.
    pad = min(.18, offset, left)
    x, sr = sf.read(media/file,start=frames(offset-pad),
                    frames=frames(right-left+pad+.18),dtype='float32')
    assert sr == rate
    initial = at(left-pad)
    times = np.r_[left-pad,np.arange(left,right,.125),right,left-pad+len(x)/rate]
    frames_in = np.round((times-left+pad)*rate).astype(int)
    frames_in = np.unique(frames_in[(frames_in >= 0) & (frames_in <= len(x))])
    frames_out = np.round(np.array([at(left-pad+f/rate)-initial for f in frames_in])*rate).astype(int)
    assert np.all(np.diff(frames_out) > 0) and frames_in[-1] == len(x)
    write = generated/name
    if file in {f'Farebi - {stem}.wav' for stem in ('drums','bass','music')}:
        guide,_ = sf.read(media/'Farebi - drums.wav',start=frames(offset-pad),
                          frames=len(x),dtype='float32')
        output = follow_drums(x,guide,frames_in/rate,frames_out/rate,frames_out[-1])
        sf.write(write,output,rate,'FLOAT')
        return at(left)-initial
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sf.write(tmp/'source.wav',x,rate,'FLOAT')
        (tmp/'map.txt').write_text(''.join(
            f'{a} {b}\n' for a,b in zip(frames_in[1:-1],frames_out[1:-1])
        ))
        run(['rubberband','-q','-3','-M',str(tmp/'map.txt'),'-D',
             str(frames_out[-1]/rate),str(tmp/'source.wav'),str(write)],check=True)
    return at(left)-initial

def move_item(match):
    item = match[0]
    start = float(field(item,'POSITION'))
    length = float(field(item,'LENGTH'))
    offset = float(field(item,'SOFFS'))
    end = start+length
    file = re.search(r'FILE "Media/([^"]+)"',item)[1]
    stem = next((s for s in stems if file == f'Farebi - {s}.wav'),None)
    edges = [start,*[t for t in bars[1:-1] if start+1e-7<t<end-1e-7],end]
    segments = []
    for index,(left,right) in enumerate(zip(edges,edges[1:])):
        mid = (left+right)/2
        p = bisect_right(bars,mid)-1
        _,bpm,ramp=definitions[p]
        # Complementary crossfades at tempo-media seams.
        actual_left = left-(.010 if index else 0)
        actual_right = right+(.010 if index<len(edges)-2 else 0)
        rate_factor = 1.
        source_offset = offset+actual_left-start
        name = file
        if ramp:
            name = f'{Path(file).stem} - ramp {round(left*1000):06d}.wav'
            source_offset = warp_segment(file,source_offset,actual_left,actual_right,name)
        elif stem and bpm == 90:
            name = f'Farebi - {stem} at source tempo.wav'
            source_offset *= 8/9
        else:
            rate_factor = bpm/80
        d = at(actual_right)-at(actual_left)
        piece = replace(item,'POSITION',f'{at(actual_left):.12f}')
        piece = replace(piece,'LENGTH',f'{d:.12f}')
        piece = replace(piece,'SOFFS',f'{source_offset:.12f}')
        piece = replace(piece,'PLAYRATE',f'{rate_factor:.12f} 1 0 -1 0 0.0025')
        for label, seam in [('FADEIN',index>0),('FADEOUT',index<len(edges)-2)]:
            fade = field(piece,label).split()
            fade[1] = f'{(abs(at((left if label=="FADEIN" else right)+.010)-at((left if label=="FADEIN" else right)-.010)) if seam else min(d/2,float(fade[1])*(d/(actual_right-actual_left)))):.12f}'
            if seam:
                fade[3] = '0'
            piece = replace(piece,label,' '.join(fade))
        if file != name:
            piece = piece.replace(f'FILE "Media/{file}"',f'FILE "Media/{name}"')
            piece = piece.replace(f'NAME "{file}"',f'NAME "{name}"')
        if index:
            for key in ['IGUID','GUID']:
                piece = replace(piece,key,'{'+str(uuid4()).upper()+'}')
        segments.append(piece)
    return '\n'.join(segments)

tempo=(stage/'Tempo map.rpp').read_text()
def tempo_block(text):
    return re.search(r'^  <TEMPOENVEX\n.*?^  >$',text,re.M|re.S)[0]
actual_points = re.findall(r'^    PT (\S+) (\S+)',tempo_block(tempo),re.M)
assert len(actual_points)==len(definitions)-1
for i,(time, b) in enumerate(actual_points):
    assert abs(float(time)-points[i])<1e-8 and float(b)==definitions[i][1]
revised = re.sub(r'^    <ITEM\n.*?^    >$',move_item,original,flags=re.M|re.S)
revised = revised.replace(tempo_block(original),tempo_block(tempo))
revised = re.sub(r'^  TEMPO 80\b','  TEMPO 90',revised,flags=re.M)
revised = re.sub(r'(?m)^(  MARKER \d+ |      PT )([\d.]+)',
                 lambda m: m[1]+f'{at(float(m[2])):.12f}',revised)
revised = revised.replace('  RENDER_RANGE 0 0 219 ',f'  RENDER_RANGE 0 0 {at(219):.12f} ')
revised = revised.replace('Muh Po Lovey Dovey v1','Muh Pe Lovey Dovey v2')
revised = re.sub(r'(?m)^    \|Farebi.*$', '    |Farebi at 90 BPM. Four instrumental tempo ramps connect both Namastute verses at their native 80 BPM.',revised)
revised = revised.replace(' unfinished\n',' single\n')
# Staging is portable via absolute paths; publication restores relative Media paths.
def render_copy(text, label, replace_media=False, wav=False):
    directory = generated if replace_media else media
    def resolve(m):
        f = (directory/m[1]) if (directory/m[1]).is_file() else media/m[1]
        assert f.is_file(),f
        return f'FILE "{f}"'
    text = re.sub(r'FILE "Media/([^"]+)"',resolve,text)
    ext='wav' if wav else 'mp3'
    text=re.sub(r'(?m)^  RENDER_FILE .*$', f'  RENDER_FILE "{stage/label}.{ext}"',text)
    if wav:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0',text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0',text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (stage/f'{label}.rpp').write_text(text)

(stage/'Portable v2.rpp').write_text(revised)
render_copy(original,'Original premaster',wav=True)
render_copy(revised,'Revised premaster',replace_media=True,wav=True)
render_copy(revised,'Revised master',replace_media=True)
print(list(zip(bars, points)))
