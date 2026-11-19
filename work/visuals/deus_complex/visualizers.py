"""Full-length stadium-photo visualizers, with still changes cut to the masters."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AUDIO = ROOT/'outputs/deus complex'
OUT = AUDIO/'visuals'
FRAMES = HERE/'visualizer_work'
W, H, FPS = 1920, 1080, 24
SIZE = W, H
R = Image.Resampling
BODONI = '/System/Library/Fonts/Supplemental/Bodoni 72.ttc'
BASKERVILLE = '/System/Library/Fonts/Supplemental/Baskerville.ttc'
AVENIR = '/System/Library/Fonts/Avenir Next.ttc'
SCALE = ['-vf','scale=out_color_matrix=bt709']
ENCODE = ['-c:v','libx264','-preset','veryfast','-crf','17','-threads','3',
          '-g','48','-keyint_min','24','-pix_fmt','yuv420p','-color_range','tv',
          '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709']


@dataclass(frozen=True)
class Track:
    slug: str
    title: str
    palette: tuple
    crops: tuple
    return_at: float
    closing: float
    treatment: str


TRACKS = (
    Track('the_things_i_created', 'The Things I Created',
          ((12,12,14),(115,83,65),(233,216,183),.59),
          ((60,526,758),(68,610,744),(73,658,731)),
          15.157895,116.210526,'crowd'),
    Track('this_must_be_heaven', 'This Must Be Heaven',
          ((11,16,25),(136,101,75),(247,224,174),.61),
          ((61,505,755),(64,580,753),(71,493,740)),
          73.785714,144.0,'cloud'),
    Track('50_calls', '50 Calls',
          ((10,11,21),(91,93,128),(215,214,236),.66),
          ((61,568,755),(74,617,733),(60,525,757)),
          60.0,72.0,'rain'),
    Track('go_back_to_the_part_where_i_leave', 'Go Back to the Part Where I Leave',
          ((13,13,15),(113,90,82),(225,215,197),.77),
          ((60,527,755),(67,615,744),(83,675,714)),
          132.414,209.655193,'rewind'),
    Track('for_my_kids_kids', 'For My Kids’ Kids',
          ((6,17,21),(64,110,105),(200,233,220),.56),
          ((61,594,756),(74,638,734),(62,552,752)),
          77.391304,143.29742,'orbit'),
)


def command(*args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)


def font(path, size, index):
    return ImageFont.truetype(path,round(size),index=index)


def text_line(mask,text,path,index,size,x,y,width,alignment='left',tracking=0):
    draw=ImageDraw.Draw(mask)
    face=font(path,size,index)
    advance=lambda f: f.getlength(text)+max(0,len(text)-1)*tracking
    if advance(face)>width:
        face=font(path,size*width/advance(face),index)
    left=x-advance(face)/2 if alignment=='center' else x
    if tracking:
        for char in text:
            draw.text((round(left),y),char,font=face,fill=255,anchor='lt')
            left+=face.getlength(char)+tracking
    else:
        draw.text((round(left),y),text,font=face,fill=255,anchor='lt')


def type_layer(track):
    style=track.treatment
    mask=Image.new('L',SIZE)
    line=lambda text,path,index,size,x,y,width,align='left',tracking=0: text_line(
        mask,text,path,index,size,x,y,width,align,tracking)
    if style=='crowd':
        line('THE THINGS',BODONI,2,154,104,127,930)
        line('I CREATED',BODONI,2,154,102,251,930)
        line('DEUS COMPLEX',AVENIR,5,24,109,391,360,tracking=4.4)
    elif style=='cloud':
        line('THIS MUST BE',BASKERVILLE,0,68,960,99,870,'center',5.8)
        line('Heaven',BODONI,1,199,959,165,1020,'center')
        line('DEUS COMPLEX',AVENIR,5,21,960,352,400,'center',4.6)
    elif style=='rain':
        line('50',BODONI,2,315,92,119,630)
        line('CALLS',AVENIR,8,87,106,356,540,tracking=11)
        line('DEUS COMPLEX',AVENIR,5,21,111,475,360,tracking=4.6)
    elif style=='rewind':
        line('GO BACK TO THE',AVENIR,8,46,109,107,775,tracking=6)
        line('PART WHERE',BODONI,2,147,103,170,1000)
        line('I LEAVE',BODONI,1,157,97,284,790)
        line('DEUS COMPLEX',AVENIR,5,21,109,447,375,tracking=4.4)
    else:
        line('FOR MY',AVENIR,8,53,108,107,670,tracking=7)
        line('KIDS’ KIDS',BODONI,2,164,100,178,1080)
        line('DEUS COMPLEX',AVENIR,5,21,111,333,375,tracking=4.6)

    rng=np.random.default_rng(7163)
    fibers=Image.fromarray(rng.uniform(0,1,(440,780)).astype(np.float32)).resize(SIZE,R.BILINEAR)
    density=np.asarray(fibers)
    opacity=np.where(density<.23,.48,np.where(density<.31,.76,1.0))
    opacity*=np.clip(.99+rng.normal(0,.082,(H,W)),.68,1)
    mask=Image.fromarray(np.uint8(np.asarray(mask)*opacity))
    ink={
        'crowd':(233,222,200),'cloud':(246,226,187),'rain':(224,221,238),
        'rewind':(230,215,204),'orbit':(224,244,228),
    }[style]
    title=Image.new('RGBA',SIZE,ink+(0,))
    title.putalpha(mask)
    return title


def grade(image,palette,exposure=1.0):
    shadow,middle,white,strength=palette
    mapping=[]
    for channel in range(3):
        mapping.extend(int(np.clip(v*exposure,0,255)) for v in np.interp(
            np.arange(256),[0,95,255],[shadow[channel],middle[channel],white[channel]]))
    tinted=ImageOps.grayscale(image).convert('RGB').point(mapping)
    return Image.blend(image,tinted,strength)


def texture(treatment):
    x=np.linspace(0,1,W)[None,:]
    y=np.linspace(0,1,H)[:,None]
    corner=np.clip(((x-.51)/.72)**2+((y-.52)/.84)**2,0,1)
    if treatment=='cloud':
        title_shade=np.exp(-((y-.18)/.24)**2)*.49
    else:
        strength={'crowd':.58,'rain':.76,'rewind':.62,'orbit':.58}[treatment]
        title_shade=strength*np.exp(-((x-.14)/.49)**2-((y-.22)/.34)**2)
    alpha=np.clip(.08+.26*corner+title_shade,0,.84)
    matte=Image.new('RGBA',SIZE,(5,6,8,0))
    matte.putalpha(Image.fromarray(np.uint8(255*alpha)))

    rng=np.random.default_rng(94913)
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    paper=np.asarray(Image.fromarray(rng.normal(0,.64,(310,550)).astype(np.float32)).resize(SIZE,R.BILINEAR))
    grain=fine+.9*paper
    shade=np.where(grain>=0,230,5).astype(np.uint8)
    alpha=np.uint8(np.clip(abs(grain)*4.2,0,18))
    paper=Image.fromarray(np.dstack((shade,shade,shade,alpha)),'RGBA')
    return matte,paper


def backgrounds(track):
    image=Image.open(HERE/'stage_source.png').convert('RGB')
    pictures=[]
    for index,(x,y,width) in enumerate(track.crops):
        height=width*H/W
        plate=image.transform(SIZE,Image.Transform.EXTENT,(x,y,x+width,y+height),R.BICUBIC)
        exposure=(.95,1.08,.76)[index]
        plate=grade(plate,track.palette,exposure)
        pictures.append(plate)
    return pictures


def compose(plate,layers):
    image=plate.convert('RGBA')
    for layer in layers:
        image.alpha_composite(layer)
    return image.convert('RGB')


def still_segment(image,path,frames):
    command('-loop','1','-framerate',FPS,'-i',image,*SCALE,*ENCODE,
            '-frames:v',frames,'-an',path)


def artwork(track,folder):
    title=type_layer(track)
    layers=(*texture(track.treatment),title)
    plates=backgrounds(track)
    for idx,plate in enumerate(plates):
        picture=compose(plate,layers)
        picture.save(folder/f'Still {idx}.jpg',quality=95,subsampling=0)


def encode(track,index,only_proofs=False):
    folder=FRAMES/track.slug
    folder.mkdir(parents=True,exist_ok=True)
    artwork(track,folder)
    if only_proofs:
        return
    source=AUDIO/f'{track.slug}.mp3'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:format_tags=artist',
                                              '-of','json',str(source)]))['format']
    duration=float(probe['duration'])
    total=int(np.ceil(duration*FPS))
    end=round(track.return_at*FPS)
    outro=round(track.closing*FPS)
    assert 0<end<outro<total
    names=['Opening','Return','Closing']
    print(f'{index:02d} {track.title} | {duration:.2f}s',flush=True)
    still_segment(folder/'Still 0.jpg',folder/'Opening.mp4',end)
    still_segment(folder/'Still 1.jpg',folder/'Return.mp4',outro-end)
    still_segment(folder/'Still 2.jpg',folder/'Closing.mp4',total-outro)
    listing=folder/'Segments.txt'
    listing.write_text(''.join(f"file '{name}.mp4'\n" for name in names))
    output=OUT/f'{index:02d} {track.title}.mp4'
    temporary=folder/'Export.mp4'
    command('-f','concat','-safe','0','-i',listing,'-i',source,'-map','0:v','-map','1:a',
            '-map_metadata','-1','-c:v','copy','-c:a','aac','-b:a','320k',
            '-movflags','+faststart','-metadata',f'title={track.title}',
            '-metadata',f'artist={probe["tags"]["artist"]}','-metadata','album=deus complex',
            '-t',f'{duration:.6f}',temporary)
    temporary.replace(output)
    print(f'Finished {output.name}',flush=True)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--proofs',action='store_true')
    parser.add_argument('--track',type=int,choices=range(1,6))
    args=parser.parse_args()
    selected=[(idx,t) for idx,t in enumerate(TRACKS,1) if args.track is None or idx==args.track]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda row: encode(row[1],row[0],args.proofs),selected))
