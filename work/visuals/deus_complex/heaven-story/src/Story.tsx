import {Audio} from '@remotion/media';
import {loadFont} from '@remotion/fonts';
import {
  AbsoluteFill, CanvasImage, Interactive, Track, interpolate, random,
  staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import timing from '../public/timing.json';

loadFont({family: 'Instrument', url: staticFile('fonts/InstrumentSerif-Regular.ttf'), weight: '400'});
loadFont({family: 'Instrument', url: staticFile('fonts/InstrumentSerif-Italic.ttf'), style: 'italic', weight: '400'});
loadFont({family: 'Archivo', url: staticFile('fonts/ArchivoNarrow.ttf'), weight: '400 700'});

const CLAMP = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const INK = '#080d0f';
const PAPER = '#dedccf';

type SceneType = 'threshold' | 'roof' | 'portrait' | 'orb' | 'slices' | 'echo' | 'tunnel' | 'contact' | 'negative' | 'eclipse' | 'release' | 'warmth' | 'ascent' | 'closing';
type SceneProps = {kind: SceneType; accent: string; length: number};

const Plate = ({width = 1080, top = 0, left = 0, opacity = 1, filter = '', image = 'stadium.jpg'}: {
  width?: number; top?: number; left?: number; opacity?: number; filter?: string; image?: string;
}) => <CanvasImage src={staticFile(image)} style={{position: 'absolute', width, height: width * 1112 / 751, top, left, opacity, filter}} />;

const Orbit = ({accent, progress, pulse, eclipse = false}: {accent: string; progress: number; pulse: number; eclipse?: boolean}) => (
  <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
    <defs>
      <radialGradient id="orb-light"><stop offset="0" stopColor={accent} stopOpacity=".25"/><stop offset="1" stopColor={accent} stopOpacity="0"/></radialGradient>
      <linearGradient id="arc-light" x1="0" x2="1"><stop offset="0" stopColor={accent} stopOpacity="0"/><stop offset=".45" stopColor={accent}/><stop offset="1" stopColor={PAPER} stopOpacity=".35"/></linearGradient>
    </defs>
    <ellipse cx="540" cy="1265" rx={530 + progress * 32} ry="450" fill="url(#orb-light)"/>
    <g style={{transformOrigin: '540px 1265px', rotate: `${-19 + progress * 12}deg`}}>
      <ellipse cx="540" cy="1265" rx="482" ry={148 + progress * 22} stroke="url(#arc-light)" strokeWidth={2.2 + pulse * .6} fill="none"/>
      <ellipse cx="540" cy="1265" rx="490" ry="159" stroke={accent} strokeOpacity=".17" strokeWidth=".8" fill="none"/>
    </g>
    {eclipse && <circle cx="540" cy={980 - progress * 90} r="310" fill={INK} stroke={accent} strokeOpacity=".5" strokeWidth="1"/>}
  </svg>
);

const SceneInner = ({kind, accent, length}: SceneProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = Math.min(1, frame / Math.max(1, length - 1));
  const t = frame / fps;
  const pulse = Math.exp(-(((t * 105 / 60) % 1) * 8));
  const brightness = 1 + pulse * .027;
  return <AbsoluteFill style={{backgroundColor: INK, overflow: 'hidden'}}>
    {kind === 'threshold' && <>
      <div style={{position: 'absolute', inset: 0, scale: interpolate(frame, [0, length], [1.05, 1.005], CLAMP)}}>
        <Plate top={-14} width={1330} left={-125} filter="saturate(.55) brightness(.79)"/>
      </div>
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(#050b0d 2%,transparent 66%)'}}/>
      <Interactive.Div name="Opening title" style={{position: 'absolute', top: 382, left: 103, color: PAPER, fontFamily: 'Instrument', fontSize: 125, lineHeight: .84, letterSpacing: -3, opacity: interpolate(frame, [0, 14], [0, 1], CLAMP)}}>This must<br/>be <i>heaven.</i></Interactive.Div>
      <Orbit accent={accent} progress={p} pulse={pulse}/>
    </>}
    {kind === 'roof' && <>
      <div style={{position: 'absolute', inset: 0, translate: `${-p * 70}px ${p * 18}px`, scale: 1.06}}>
        <Plate width={2350} left={-370} top={-655} filter="grayscale(.35) contrast(1.12) brightness(1.08)"/>
      </div>
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(0deg,#0a1114 0%,transparent 62%)'}}/>
      <svg style={{position: 'absolute', top: 350, left: 80}} width="920" height="1060"><path d={`M0 790 L460 ${120 + p * 150} L920 790`} stroke={accent} strokeOpacity=".48" strokeWidth="1.4" fill="none"/><path d="M0 805H920" stroke={accent} strokeOpacity=".24" strokeWidth="1"/></svg>
    </>}
    {kind === 'portrait' && <>
      <div style={{position: 'absolute', inset: 0, scale: 1.03 + p * .055, transformOrigin: '50% 66%'}}>
        <Plate width={1810} left={-465} top={-565} filter="saturate(.35) contrast(1.13)"/>
      </div>
      <div style={{position: 'absolute', inset: 0, background: `linear-gradient(90deg,${accent}10,transparent 62%)`, mixBlendMode: 'screen'}}/>
      <div style={{position: 'absolute', top: 295, left: 125, width: 16, height: 220, borderLeft: `1px solid ${PAPER}70`}}/>
    </>}
    {kind === 'orb' && <>
      <div style={{position: 'absolute', inset: 0, scale: 1.08 + p * .04, translate: `${-p * 25}px 0px`}}>
        <Plate width={2380} left={-600} top={-1635} filter="saturate(.45) contrast(1.17)"/>
      </div>
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(#050d13bb,transparent 60%,#050d13)'}}/>
      <div style={{position: 'absolute', left: 540, top: 340, width: 1, height: 930, background: `linear-gradient(transparent,${accent},transparent)`, rotate: '-24deg', opacity: .44}}/>
    </>}
    {kind === 'slices' && <>
      <Plate width={1330} left={-125} top={-25} filter="grayscale(.68) brightness(.70)"/>
      {[0,1,2].map((i) => <div key={i} style={{position: 'absolute', left: 72 + i * 316, top: 375 + i * 38, width: 302, height: 1005, overflow: 'hidden', borderTop: `2px solid ${accent}`, translate: `0px ${Math.sin(p * Math.PI + i) * 26}px`}}>
        <Plate width={1600} left={-565 + i * 100} top={-630 + i * 38} filter={`saturate(.6) brightness(${.9 + i * .16})`}/>
      </div>)}
    </>}
    {kind === 'echo' && <>
      <Plate width={1530} left={-225} top={-290} filter="grayscale(.45) contrast(1.1) brightness(.78)"/>
      <div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', opacity: .17 + pulse * .025, translate: `${26 + p * 45}px ${-p * 20}px`}}><Plate width={1530} left={-225} top={-290} filter="sepia(.8) hue-rotate(120deg) saturate(1.1)"/></div>
      <Orbit accent={accent} progress={p} pulse={pulse}/>
    </>}
    {kind === 'tunnel' && <>
      <Plate width={2280} top={-610} left={-610} filter="grayscale(.45) brightness(.94) contrast(1.10)"/>
      {Array.from({length: 7}, (_,i) => <div key={i} style={{position: 'absolute', width: 760 - i * 80, height: 1040 - i * 110, top: 354 + i * 55, left: 160 + i * 40, border: `1px solid ${accent}${i < 3 ? '74' : '32'}`, scale: 1 + p * .08, rotate: `${(i - 3) * .26}deg`}}/>)}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 55%,transparent 10%,#03090a99 88%)'}}/>
    </>}
    {kind === 'contact' && <>
      <div style={{position: 'absolute', inset: 0, backgroundColor: '#d8d4c6'}}/>
      <div style={{position: 'absolute', left: 73, top: 270, width: 934, height: 1260, overflow: 'hidden', rotate: `${-.7 + p * 1.2}deg`}}>
        <Plate width={1120} left={-90} top={-300} filter="grayscale(1) contrast(1.4) brightness(.95)"/>
      </div>
      <div style={{position: 'absolute', left: 74, top: 1600, width: 929, borderTop: '2px solid #242525'}}/>
      <CanvasImage src={staticFile('grain/03.png')} style={{position: 'absolute', inset: 0, width: 1080, height: 1920, mixBlendMode: 'multiply', opacity: .1}}/>
    </>}
    {kind === 'negative' && <>
      <div style={{position: 'absolute', inset: 0, scale: 1.05 + p * .06}}><Plate width={1660} left={-280} top={-490} filter="invert(.94) grayscale(1) contrast(1.1)"/></div>
      <div style={{position: 'absolute', inset: 0, background: '#492c1317', mixBlendMode: 'multiply'}}/>
      <div style={{position: 'absolute', top: 471, left: 294, width: 492, height: 492, border: '2px solid #493323', borderRadius: '50%', scale: .96 + p * .12}}/>
    </>}
    {kind === 'eclipse' && <>
      <Plate width={1340} left={-130} top={-28} filter="grayscale(.6) brightness(.48)"/>
      <Orbit accent={accent} progress={p} pulse={pulse} eclipse/>
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse at 50% 56%,${accent}18,transparent 59%)`, mixBlendMode: 'screen'}}/>
    </>}
    {kind === 'release' && <>
      <div style={{position: 'absolute', inset: 0, scale: interpolate(frame,[0,length],[1.17,1.02],CLAMP), transformOrigin: '50% 66%'}}><Plate width={1350} left={-135} top={-13} filter={`saturate(.78) brightness(${brightness})`}/></div>
      <Orbit accent={accent} progress={p} pulse={pulse}/>
      <div style={{position: 'absolute', left: 88, top: 310, fontFamily: 'Instrument', fontStyle: 'italic', fontSize: 240, letterSpacing: -11, lineHeight: .8, color: PAPER, opacity: interpolate(frame, [0, 12, length-18, length], [0,.88,.88,0],CLAMP), mixBlendMode: 'screen'}}>heaven</div>
      <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg,${accent}28,transparent 70%)`, mixBlendMode: 'screen'}}/>
    </>}
    {kind === 'warmth' && <>
      <div style={{position: 'absolute', inset: 0, scale: 1.02+p*.06}}><Plate width={1840} left={-380} top={-770} filter="sepia(.5) saturate(.8) contrast(1.13)"/></div>
      <div style={{position: 'absolute', left: -120 + p * 220, top: -100, width: 660, height: 2050, rotate: '-14deg', background: `linear-gradient(90deg,transparent,${accent}35,transparent)`, mixBlendMode: 'screen'}}/>
    </>}
    {kind === 'ascent' && <>
      <Plate width={1380} left={-150} top={-40 - p*75} filter="saturate(.45) contrast(1.18)"/>
      <svg width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        {Array.from({length:10},(_,i)=><path key={i} d={`M${90+i*100} 1670 L${450+i*20} ${195 + p * 70}`} stroke={accent} strokeOpacity={.12+i%3*.06} strokeWidth="1"/>)}
      </svg>
      <Orbit accent={accent} progress={p} pulse={pulse}/>
    </>}
    {kind === 'closing' && <>
      <div style={{position: 'absolute', inset: 0, scale: 1.04 + p*.025}}><Plate width={1320} left={-120} top={-20} filter="saturate(.50) contrast(1.08) brightness(.86)"/></div>
      <Orbit accent={accent} progress={p} pulse={pulse}/>
      <Interactive.Div name="Closing song title" style={{position: 'absolute', left: 92, top: 332, color: PAPER, fontFamily: 'Instrument', fontSize: 127, letterSpacing: -3, lineHeight: .85, opacity: interpolate(frame,[0,15],[0,1],CLAMP)}}>This must<br/>be <i>heaven.</i></Interactive.Div>
      <Interactive.Div name="Closing album title" style={{position: 'absolute', left: 98, top: 590, color: PAPER, fontFamily: 'Archivo', fontSize: 39, letterSpacing: 7, opacity: .76}}>DUES COMPLEX</Interactive.Div>
    </>}
  </AbsoluteFill>;
};

const Scene = Interactive.create({Component: SceneInner, layout: 'absolute-fill', schema: {
  kind: {type: 'string', default: 'portrait', description: 'Shot'},
  accent: {type: 'color', default: '#a4d4d8', description: 'Light color'},
  length: {type: 'number', default: 137, description: 'Animation frames', hiddenFromList: true},
}});

const FilmSurface = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame/fps;
  const cuts = timing.cutsSeconds.slice(1,-1);
  const nearCut = Math.min(...cuts.map(c => Math.abs(c - t)));
  const flash = Math.max(0,1-nearCut/.065);
  const bass = Math.min(1.3, timing.pulse[Math.min(frame,timing.pulse.length-1)] || 0);
  const typeColor = t >= 29.285714286 && t < 38.428571429 ? '#252725' : PAPER;
  return <>
    <CanvasImage src={staticFile(`grain/${String(Math.floor(frame/3)%12).padStart(2,'0')}.png`)} style={{position: 'absolute', inset: 0, width: 1080, height: 1920, pointerEvents: 'none', mixBlendMode: 'soft-light', opacity: .22, translate: `${Math.floor(random(frame)*12)-6}px ${Math.floor(random(frame+200)*12)-6}px`, scale: 1.025}}/>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 53%,transparent 24%,#0308088a 100%)', pointerEvents: 'none'}}/>
    <AbsoluteFill style={{backgroundColor: t<40.7 ? '#acd8d9' : '#e0c9aa', mixBlendMode: 'screen', opacity: flash * .23 + bass * .008}}/>
    <AbsoluteFill style={{border: '1px solid #c7c2ae25', inset: 32, width: 1016, height: 1856, pointerEvents: 'none'}}/>
    <div style={{position: 'absolute', left: 82, bottom: 210, fontFamily: 'Archivo', color: typeColor, fontSize: 39, letterSpacing: 1, opacity: t>54.4 ? 0 : .80, textShadow: typeColor === PAPER ? '0 2px 14px #060b0d' : 'none'}}>This must be heaven</div>
    <Interactive.Div name="Album credit" style={{position: 'absolute', top: 200, left: 84, fontFamily: 'Archivo', fontWeight: 500, color: typeColor, fontSize: 32, letterSpacing: 6, opacity: t>54.4 ? 0 : .65}}>DUES COMPLEX</Interactive.Div>
    <AbsoluteFill style={{backgroundColor: INK, opacity: interpolate(frame,[0,7,1746,1770],[.60,0,0,1],CLAMP), pointerEvents: 'none'}}/>
  </>;
};

export const HeavenStory = () => {
  const {fps} = useVideoConfig();
  return <AbsoluteFill style={{backgroundColor: INK}}>
    <Track name="Stadium film">
      <Scene name="Threshold" kind="threshold" accent="#b8dadd" length={56} durationInFrames={Math.round(1.857142857*fps)}/>
      <Scene name="Roof geometry" kind="roof" accent="#a0d6dd" length={137} from={Math.round(1.857142857*fps)} durationInFrames={137}/>
      <Scene name="Performer in the crowd" kind="portrait" accent="#abcbd0" length={137} from={Math.round(6.428571429*fps)} durationInFrames={137}/>
      <Scene name="Dome material" kind="orb" accent="#a8d9d9" length={137} from={11*fps} durationInFrames={137}/>
      <Scene name="Fractured photograph" kind="slices" accent="#9ec6c9" length={137} from={Math.round(15.571428571*fps)} durationInFrames={137}/>
      <Scene name="Double exposure" kind="echo" accent="#93c4c9" length={137} from={Math.round(20.142857143*fps)} durationInFrames={137}/>
      <Scene name="Impossible architecture" kind="tunnel" accent="#7aa5ad" length={138} from={Math.round(24.714285714*fps)} durationInFrames={138}/>
      <Scene name="Contact print" kind="contact" accent="#baac91" length={137} from={Math.round(29.285714286*fps)} durationInFrames={137}/>
      <Scene name="Negative frame" kind="negative" accent="#bbad96" length={137} from={Math.round(33.857142857*fps)} durationInFrames={137}/>
      <Scene name="Before the light" kind="eclipse" accent="#cbbc9f" length={68} from={Math.round(38.428571429*fps)} durationInFrames={68}/>
      <Scene name="Chorus release" kind="release" accent="#dfc5a8" length={138} from={Math.round(40.714285714*fps)} durationInFrames={138}/>
      <Scene name="Warm projection" kind="warmth" accent="#bd754d" length={137} from={Math.round(45.285714286*fps)} durationInFrames={137}/>
      <Scene name="Ascent" kind="ascent" accent="#e6d5b6" length={137} from={Math.round(49.857142857*fps)} durationInFrames={137}/>
      <Scene name="Final photograph" kind="closing" accent="#dbcdaf" length={137} from={Math.round(54.428571429*fps)} durationInFrames={137}/>
    </Track>
    <Track name="Music"><Audio name="Continuous song excerpt" src={staticFile('music.wav')} durationInFrames={59*fps}/></Track>
    <FilmSurface/>
  </AbsoluteFill>;
};
