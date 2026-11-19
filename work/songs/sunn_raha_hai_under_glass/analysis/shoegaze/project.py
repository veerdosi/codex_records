"""Stage the stem mix, automation and export settings in a portable REAPER session."""
import json
from pathlib import Path
import re
from uuid import uuid4

Here=Path(__file__).resolve().parent
Song=Here.parents[1]
Root=Song.parents[2]
Media=Song/'stems/shoegaze'
Template=Root/'reaper/This Must Be Heaven/This Must Be Heaven.rpp'
Title='Sunn Raha Hai (Under Glass)'
Artist='Shreya Ghoshal, Veer'
Duration=182.06736961451247
Sections=json.loads((Song/'analysis/arrangement.json').read_text())['sections']
Names=('Shreya lead','Vocal room','Guitar motif and air','Glide guitars','Picked bass','Live kit')
faders=(1.25,0.,.35,-.6,-.65,0.)
rides={
    'Shreya lead': [(0,0),(81.8,0),(83.80,.85),(93.94,.85),(94.52,0),
                    (147.65,0),(149.85,1.0),(171.12,1.0),(171.65,0)],
    'Glide guitars': [(0,-5),(4.20,-3.4),(10.62,-3.1),(11.32,-5.2),(33.03,-5.2),
                      (33.72,-4.0),(50.02,-4.0),(50.68,-3.2),(72.6,-3.2),
                      (73.1,-2.),(83.5,-1.8),(84.29,0),(93.97,0),(94.35,0),
                      (102.15,-4.2),(112.2,-4.2),(122.23,-4.0),(138.45,-3),
                      (140.5,-2.0),(149.57,-1.9),(150.32,0),(170.94,0),(171.46,-1.5),
                      (176.2,-2.2),(182.,-3.7)],
    'Picked bass': [(0,0),(149.4,0),(150.318,-.45),(171.6,-.45),(172.5,0)],
}
colors=(12232731,9404333,10837869,13070938,9219702,15771194)


def guid():
    return '{'+str(uuid4()).upper()+'}'


def amp(db):
    return 10**(db/20)


def track(i, level):
    name=Names[i]
    points=rides.get(name,[])
    envelope=''
    if points:
        envelope = f'''    <VOLENV3
      EGUID {guid()}
      ACT 1 -1
      VIS 1 1 1
      LANEHEIGHT 0 0
      ARM 0
      DEFSHAPE 0 -1 -1
      VOLTYPE 1
'''
        envelope += ''.join(f'      PT {t:.9f} {amp(db):.12f} 0\n' for t,db in points)+'    >\n'
    return f'''  <TRACK {guid()}
    NAME "{name}"
    PEAKCOL {colors[i]}
    BEAT 0
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN {amp(level):.12f} 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    NCHAN 2
    FX 1
    MAINSEND 1 0
{envelope}    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH {Duration:.12f}
      LOOP 0
      ALLTAKES 0
      FADEIN 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      FADEOUT 1 0.003 0 1 0 0 0 1 0 0 1 0 0
      MUTE 0 0
      SEL 0
      IGUID {guid()}
      IID {i+1}
      NAME "{name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {guid()}
      <SOURCE WAVE
        FILE "Media/{name}.wav"
      >
    >
  >
'''


def project():
    header=Template.read_text().split('  MARKER 1 ',1)[0]
    for before,after in (('This Must Be Heaven',Title),('Kanye West, Tame Impala & Veer',Artist),
                         ('deus complex','single'),('TEMPO 105 ', 'TEMPO 85.42 '),('LOCK 1\n','LOCK 0\n')):
        header=header.replace(before,after)
    header=re.sub(r'(?m)^  RENDER_RANGE .*$',f'  RENDER_RANGE 0 0 {Duration} 0 1000',header)
    header=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 193 0.194984 0.836566 0 0 1 1',header)
    header=header.replace('  RENDER_FILE ""','  RENDER_FILE "Renders/Under Glass.mp3"')
    header=header.replace('  <NOTES 0 2\n', '  <NOTES 0 2\n    |Shoegaze arrangement. Original Shreya Ghoshal vocal timing.\n')
    # Each refrain ends with a two-beat bar. Preserve both vocal pickups
    # and label the following section on beat one.
    signatures=((0,4),(132,2),(134,4),(242,2),(244,4))
    meter=''.join(
        f'    PT {beat*60/85.42:.12f} 85.42 1 {262144+count} 0 1 0 "" 0 {169 if count==4 else 9} 0 {"ABBB" if count==4 else "AB"}\n'
        for beat,count in signatures
    )
    header=header.replace('  >\n  RULERHEIGHT',meter+'  >\n  RULERHEIGHT',1)
    for i,section in enumerate(Sections,1):
        start,end = section['start'], section['end']
        header += f'  MARKER {i} {start:.12f} "{section["name"].title()}" 1 0 1 B {guid()} 0 1\n'
        header += f'  MARKER {i} {end:.12f} "" 1\n'
    return header+'  <PROJBAY\n  >\n'


def staging(label, header, tracks, mp3=False):
    text=header+''.join(tracks)+'>\n'
    text=re.sub(r'(?m)^(\s+FILE )"Media/([^"]+)"$',
                lambda m:f'{m[1]}"{Media/m[2]}"',text)
    file=Here/(label+('.mp3' if mp3 else '.wav'))
    text=re.sub(r'(?m)^  RENDER_FILE .*$',f'  RENDER_FILE "{file}"',text)
    if not mp3:
        text=re.sub(r'(?m)^  RENDER_NORMALIZE .*$', '  RENDER_NORMALIZE 0 0 0 0 0 0 0', text)
        text=re.sub(r'(?m)^  RENDER_STEMS .*$', '  RENDER_STEMS 0', text)
        text=re.sub(r'(?ms)(^  <RENDER_CFG\n).*?(^  >)',r'\g<1>    ZXZhdxgAAQ==\n\2',text)
    (Here/(label+'.rpp')).write_text(text)


if __name__=='__main__':
    header=project()
    tracks=[track(i,gain) for i,gain in enumerate(faders)]
    (Here/(Title+'.rpp')).write_text(header+''.join(tracks)+'>\n')
    staging('Master',header,tracks,mp3=True)
    staging('Premaster',header,tracks)
    staging('Backing',header,tracks[2:])
    staging('Voice',header,tracks[:2])
    staging('Drums',header,tracks[-1:])
    staging('Guitars',header,tracks[2:4])
