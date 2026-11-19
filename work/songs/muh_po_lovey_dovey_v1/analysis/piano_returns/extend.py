"""Extend the native-tempo turnarounds by one bar each."""
import re
from uuid import uuid4

# Only the backing spans these cut points. In each case the preceding
# bar uses the same E-based harmony and drum phase.
INSERTS = (96.,180.)
ITEM = re.compile(r'^    <ITEM\n.*?^    >$',re.M|re.S)

def get(item,key):
    return re.search(r'^      '+key+r' (.*)$',item,re.M)[1]

def set_fields(text,**fields):
    for key,value in fields.items():
        text=re.sub(r'(?m)^      '+key+r' .*$',f'      {key} {value}',text)
    return text

def guid():
    return '{'+str(uuid4()).upper()+'}'

def shift(t):
    return t+3*sum(t>=x for x in INSERTS)

def extend(project):
    def item(m):
        clip=m[0]
        p,length,offset=(float(get(clip,key)) for key in ('POSITION','LENGTH','SOFFS'))
        end=p+length
        if 'Veer - pickup keys.wav' in clip or (abs(p-94.5)<1e-6 and 'Veer - harmony' in clip):
            return ''
        cuts=[x for x in INSERTS if p<x<end]
        if not cuts:
            return set_fields(clip,POSITION=shift(p))
        assert len(cuts)==1 and any(f'Farebi - {s}.wav' in clip for s in ('drums','bass','music'))
        cut=cuts[0]
        cutpos=shift(cut)-3
        def part(a,b,source,fi,fo,new):
            return set_fields(clip,POSITION=a,LENGTH=b-a,SOFFS=source,
                FADEIN=re.sub(r'^1 \S+',f'1 {fi}',get(clip,'FADEIN')),
                FADEOUT=re.sub(r'^1 \S+',f'1 {fo}',get(clip,'FADEOUT')),
                **({'GUID':guid(),'IGUID':guid()} if new else {}))
        edge=.009
        fade_in=float(get(clip,'FADEIN').split()[1])
        fade_out=float(get(clip,'FADEOUT').split()[1])
        return '\n'.join([
            part(shift(p),cutpos+edge,offset,fade_in,edge*2,False),
            part(cutpos-edge,cutpos+3+edge,offset+cut-p-3-edge,edge*2,edge*2,True),
            part(cutpos+3-edge,shift(end),offset+cut-p-edge,edge*2,fade_out,True),
        ])
    project=ITEM.sub(item,project)
    return re.sub(r'(?m)^(  MARKER \d+ |      PT )([\d.]+)',
                  lambda m:m[1]+str(shift(float(m[2]))),project)
