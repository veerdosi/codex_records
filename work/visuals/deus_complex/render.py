"""Use the supplied photograph to make the Deus Complex cover and visualizers."""
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from scipy.ndimage import gaussian_filter1d

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'visuals/deus_complex'
SOURCE = HERE / 'stage_source.png'
AUDIO = ROOT / 'outputs/deus complex'
SERIF = '/System/Library/Fonts/Supplemental/Baskerville.ttc'
SANS = '/System/Library/Fonts/Avenir Next.ttc'
WORDMARK = '/System/Library/Fonts/Supplemental/Bodoni 72.ttc'
W, H, FPS = 1920, 1080, 24
PANEL = (978, 36, 906, 1008)
R = Image.Resampling


@dataclass(frozen=True)
class Track:
    slug: str
    title: tuple
    credits: tuple
    color: tuple
    tint: tuple
    curve: str
    period: float
    phase: float


TRACKS = [
    Track('the_things_i_created', ('The Things', 'I Created'), ('Kanye West · Travis Scott', 'Labi Siffre · Veer'),
          (132, 184, 196), (168, 215, 224), 'mirror', 24.0, 0.0),
    Track('this_must_be_heaven', ('This Must', 'Be Heaven'), ('Kanye West · Tame Impala · Veer',),
          (207, 190, 148), (232, 213, 173), 'rise', 28.0, 1.3),
    Track('50_calls', ('50 Calls',), ('Kanye West · Juice WRLD · Veer',),
          (177, 161, 207), (204, 185, 230), 'double', 19.0, 2.5),
    Track('blame_me_for_everything', ('Blame Me for', 'Everything'), ('Kanye West · Metro Boomin', '21 Savage · Veer'),
          (153, 182, 220), (168, 196, 236), 'wave', 33.0, 2.9),
    Track('for_my_kids_kids', ('For My', 'Kids’ Kids'), ('Kanye West · Yeat · Veer',),
          (111, 212, 213), (142, 227, 220), 'bars', 16.0, 1.1),
]


def font(size, serif=False, index=None):
    return ImageFont.truetype(SERIF if serif else SANS, size,
                             index=(0 if serif else 5) if index is None else index)


def spaced(draw, xy, text, face, fill, space):
    x, y = xy
    for letter in text:
        draw.text((x,y), letter, font=face, fill=fill, anchor='lt')
        x += face.getlength(letter)+space


def photograph():
    with Image.open(SOURCE) as image:
        assert image.size == (870,1130)
        return image.convert('RGB')


def wordmark(text, size):
    face = ImageFont.truetype(WORDMARK, 360, index=2)
    left, top, right, bottom = face.getbbox(text)
    mask = Image.new('L', (right-left+8,bottom-top+8))
    ImageDraw.Draw(mask).text((4-left,4-top),text,font=face,fill=255)
    return mask.resize(size,R.LANCZOS)


def cover():
    image = photograph().crop((60,288,817,1045)).resize((1800,1800),R.LANCZOS)
    gray = ImageOps.grayscale(image).convert('RGB')
    image = Image.blend(image,gray,.17)
    pixels = np.asarray(image,dtype=np.float32)
    rng = np.random.default_rng(382)
    fine = rng.normal(0,2.05,(1800,1800))
    coarse = Image.fromarray(rng.normal(0,1.55,(690,690)).astype(np.float32)).resize(image.size,R.BILINEAR)
    grain = (fine + np.asarray(coarse))[:,:,None]
    image = Image.fromarray(np.uint8(np.clip((pixels-3.1)*1.052+grain,0,255)))
    # Treat the lettering like a worn print across the stadium structure.
    glyph = Image.new('L',image.size)
    glyph.paste(wordmark('DEUS',(895,234)),(451,265))
    glyph.paste(wordmark('COMPLEX',(1485,223)),(156,521))
    luminance = image.convert('L')
    local = np.asarray(luminance,dtype=np.float32)
    rails = local-np.asarray(luminance.filter(ImageFilter.GaussianBlur(9)),dtype=np.float32)
    flecks = Image.fromarray(rng.random((440,440),dtype=np.float32)).resize(image.size,R.BILINEAR)
    rough = np.asarray(flecks)
    opacity = .93 - np.clip((rails-3.5)*.026,0,.53)
    opacity *= np.where(rough<.22,.46,np.where(rough<.30,.78,1.))
    opacity *= np.clip(1.09+rng.normal(0,.085,local.shape),.68,1.)
    mask = Image.fromarray(np.uint8(np.asarray(glyph)*np.clip(opacity,0,1)))
    ink = np.zeros((1800,1800,3),np.float32)+[215,216,200]
    ink += grain*2.15 + ((rough-.5)*22)[:,:,None]
    ink = Image.fromarray(np.uint8(np.clip(ink,0,255)))
    image.paste(ink,(0,0),mask)
    image.save(OUT/'deus_complex_cover.png',optimize=True)
    image.resize((720,720),R.LANCZOS).save(HERE/'Cover proof.jpg',quality=92)


def layout(track, number):
    yy,xx = np.mgrid[0:H,0:W].astype(np.float32)
    halo = np.exp(-(((xx-955)/740)**2+((yy-695)/605)**2))
    tint = np.array(track.color,dtype=np.float32)
    tint *= .095
    base = np.array([8.,12.,17.])+halo[:,:,None]*tint
    noise = np.random.default_rng(31).normal(0,.59,(H,W,1))
    image=Image.fromarray(np.uint8(np.clip(base+noise,0,255)))
    draw=ImageDraw.Draw(image)
    x=105
    mark=wordmark('DEUS COMPLEX',(325,35))
    image.paste((218,226,226),(x,112),mark)
    draw.line((x,195,823,195),fill=(47,63,72),width=1)

    face=font(123 if len(track.title)>1 else 153,serif=True)
    widest=max(face.getlength(line) for line in track.title)
    if widest>760:
        face=font(round(face.size*760/widest),serif=True)
    top=340 if len(track.title)>1 else 412
    line_height=108
    for index, line in enumerate(track.title):
        draw.text((x,top+line_height*index),line,font=face,fill=(238,241,238),anchor='lt')
    sub_top=top+line_height*len(track.title)+51
    for index, line in enumerate(track.credits):
        draw.text((x,sub_top+35*index),line,font=font(25,index=7),fill=(178,199,205),anchor='lt')

    spaced(draw,(x,947),f'{number:02d} / 05',font(20),track.color,3.6)
    draw.line((x+121,958,823,958),fill=(48,65,77),width=1)
    return image


def photo_plates(track):
    image=photograph().crop((60,147,817,1128))
    neutral=ImageOps.grayscale(image).convert('RGB')
    tint=ImageOps.colorize(ImageOps.grayscale(image),black=(4,9,15),white=track.tint)
    grade=Image.blend(image,Image.blend(neutral,tint,.78),.23)
    grade=ImageEnhance.Contrast(grade).enhance(1.07)
    _,_,pw,ph=PANEL
    sw,sh=grade.size
    width=min(sw-8,(sh-18)*pw/ph)
    height=width*ph/pw
    frames=[]
    for index in range(60):
        angle=index*2*np.pi/60
        z=1.009+.048*(.5+.5*np.cos(angle))
        w,h=width/z,height/z
        dx=7*np.sin(angle)
        dy=12*np.sin(angle+.7)
        center_x=sw/2+dx
        center_y=sh/2+31+dy
        box=(center_x-w/2,center_y-h/2,center_x+w/2,center_y+h/2)
        pane=grade.transform((pw,ph),Image.Transform.EXTENT,box,R.BICUBIC)
        frames.append(pane)
    return frames


def audio_features(path):
    rate=24000
    command=['ffmpeg','-v','error','-i',str(path),'-ac','1','-ar',str(rate),'-f','f32le','-']
    data=np.frombuffer(subprocess.check_output(command),dtype=np.float32)
    size=2048
    step=rate//FPS
    frames=int(np.ceil(len(data)/step))
    padding=np.pad(data,(size//2,size//2+step))
    windows=np.lib.stride_tricks.sliding_window_view(padding,size)[0:frames*step:step]
    spectrum=abs(np.fft.rfft(windows*np.hanning(size),axis=1))
    freqs=np.fft.rfftfreq(size,1/rate)
    edges=np.geomspace(42,9800,39)
    bands=[]
    for a,b in zip(edges,edges[1:]):
        bins=np.flatnonzero((freqs>=a)&(freqs<b))
        if not len(bins):
            bins=[np.argmin(abs(freqs-(a+b)/2))]
        bands.append(np.sqrt(np.mean(spectrum[:,bins]**2,axis=1)))
    bands=np.stack(bands,axis=1)
    envelope=np.percentile(bands,96,axis=0)
    scaled=np.clip(bands/np.maximum(envelope,.002),0,1.15)**.70
    scaled=gaussian_filter1d(scaled,.90,axis=0)
    bass=np.sqrt(np.mean(spectrum[:,(freqs>=38)&(freqs<=125)]**2,axis=1))
    bass=np.clip(bass/max(np.percentile(bass,94),.002),0,1.24)
    bass=gaussian_filter1d(bass,1.08)
    return scaled,bass,len(data)/rate


def draw_signal(draw,track,bands):
    x=np.linspace(107,793,len(bands))
    y=812
    color=track.color
    soft=tuple(round(c*.61) for c in color)
    draw.line((x[0],y,x[-1],y),fill=(44,62,71),width=1)
    if track.curve=='bars':
        for k,value in enumerate(bands):
            ht=3+54*float(value)
            draw.rounded_rectangle((x[k],y-ht/2,x[k]+5,y+ht/2),radius=2,fill=color)
        return
    if track.curve=='wave':
        side=np.sin(np.arange(len(bands))*1.82)*bands*37
        trace=[(round(a),round(y+b)) for a,b in zip(x,side)]
    else:
        height={'mirror':34,'rise':51,'double':24}[track.curve]
        trace=[(round(a),round(y-height*b)) for a,b in zip(x,bands)]
    if track.curve=='mirror':
        draw.line([(a,2*y-b) for a,b in trace],fill=soft,width=1)
    if track.curve=='double':
        draw.line([(a+2,round(y+(y-b)*.60)) for a,b in trace],fill=soft,width=2)
    draw.line(trace,fill=color,width=2,joint='curve')


def frame(track,base,pane,features,bass,at,total):
    image=base.copy()
    x,y,w,h=PANEL
    # Move only the photo's light level. The frame and typography stay locked.
    strength=round(1.5+9.0*float(bass))
    if strength:
        lookup=[min(255,int(v+strength*(v/255)**.50)) for v in range(256)]
        pane=pane.point(lookup*3)
    image.paste(pane,(x,y))
    draw=ImageDraw.Draw(image)
    draw.rectangle((x,y,x+w-1,y+h-1),outline=(44,59,70),width=1)
    draw_signal(draw,track,features)
    draw.line((226,958,226+round(597*at/max(total,1)),958),fill=track.color,width=2)
    return image


def video(track,number,still_only):
    path=AUDIO/(track.slug+'.mp3')
    features,bass,total=audio_features(path)
    base=layout(track,number)
    plates=photo_plates(track)
    duration=len(bass)/FPS
    def at(i):
        motion=int(round(60*((i/FPS)/track.period+track.phase/(2*np.pi))))%60
        return frame(track,base,plates[motion],features[i],bass[i],i/FPS,total)
    proof=min(round(FPS*11),len(bass)-1)
    at(proof).resize((960,540),R.LANCZOS).save(HERE/f'{number:02d} proof.jpg',quality=93)
    if still_only:
        return
    destination=OUT/(f'{number:02d}_{track.slug}.mp4')
    temporary=OUT/(f'.{number:02d}_{track.slug}.rendering.mp4')
    title=' '.join(track.title)
    args=['ffmpeg','-hide_banner','-loglevel','error','-y',
          '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0',
          '-i',str(path),'-map','0:v:0','-map','1:a:0','-map_metadata','-1',
          '-c:v','h264_videotoolbox','-pix_fmt','yuv420p','-b:v','4500k','-maxrate','7500k','-bufsize','9000k',
          '-profile:v','high','-g','72','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
          '-vf','scale=out_color_matrix=bt709','-c:a','aac','-b:a','320k',
          '-movflags','+faststart','-metadata',f'title={title}','-metadata','album=Deus Complex',
          '-metadata',f'track={number}/5','-t',f'{duration:.6f}',str(temporary)]
    with subprocess.Popen(args,stdin=subprocess.PIPE) as process:
        try:
            for i in range(len(bass)):
                process.stdin.write(at(i).tobytes())
                if i%(FPS*30)==0:
                    print(f'{number:02d}: {i/FPS:.0f}/{total:.0f}s',flush=True)
        finally:
            process.stdin.close()
        if process.wait()!=0:
            raise RuntimeError(f'FFmpeg failed for {title}')
    temporary.replace(destination)
    print(f'Finished {destination.name}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track',type=int,choices=range(0,len(TRACKS)+1),help='0 makes the cover')
    parser.add_argument('--still',action='store_true',help='make a proof frame only')
    args=parser.parse_args()
    if args.track==0:
        cover()
    else:
        video(TRACKS[args.track-1],args.track,args.still)
