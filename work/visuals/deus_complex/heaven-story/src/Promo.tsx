import {Audio} from '@remotion/media';
import {
  AbsoluteFill, CanvasImage, Interactive, Sequence, Track,
  interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {HeavenStory} from './Story';

const CLAMP = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const PAPER = '#dedccf';

const CardSurface = () => {
  const frame = useCurrentFrame();
  return <>
    <CanvasImage src={staticFile(`grain/${String(Math.floor(frame/3)%12).padStart(2,'0')}.png`)} style={{position:'absolute',inset:0,width:1080,height:1920,mixBlendMode:'soft-light',opacity:.18}}/>
    <AbsoluteFill style={{background:'radial-gradient(ellipse at 65% 80%,transparent,#050a0c88)'}}/>
    <div style={{position:'absolute',inset:32,border:'1px solid #c7c2ae25'}}/>
  </>;
};

const Introduction = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return <AbsoluteFill style={{backgroundColor:'#080f12',overflow:'hidden'}}>
    <CanvasImage src={staticFile('stadium.jpg')} style={{position:'absolute',width:1380,height:2043,left:-150,top:45,opacity:.32,filter:'blur(6px) saturate(.45)',scale:interpolate(frame,[0,5.5*fps],[1,1.035],CLAMP)}}/>
    <AbsoluteFill style={{background:'linear-gradient(#080f12 8%,#080f12e8 50%,#080f1288)'}}/>
    <CardSurface/>
    <Interactive.Div name="Personal intro" style={{position:'absolute',top:405,left:100,right:96,color:PAPER,fontFamily:'Archivo',fontSize:64,lineHeight:1.13,letterSpacing:-.8,opacity:interpolate(frame,[5,20],[0,1],CLAMP),translate:interpolate(frame,[5,23],['0px 13px','0px 0px'],CLAMP)}}>
      been messing around<br/>with music production.
    </Interactive.Div>
    <Interactive.Div name="Collaboration setup" style={{position:'absolute',top:710,left:98,right:90,color:PAPER,fontFamily:'Instrument',fontSize:91,lineHeight:1.04,letterSpacing:-1.3,opacity:interpolate(frame,[25,41],[0,1],CLAMP),translate:interpolate(frame,[25,44],['0px 13px','0px 0px'],CLAMP)}}>
      here’s my take on<br/><span style={{fontSize:113}}>kanye west ×<br/><i>tame impala.</i></span>
    </Interactive.Div>
    <Interactive.Div name="Album signature" style={{position:'absolute',left:103,bottom:250,color:PAPER,fontFamily:'Archivo',fontSize:31,letterSpacing:6,opacity:.55}}>DUES COMPLEX</Interactive.Div>
  </AbsoluteFill>;
};

const YouTubeEnd = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{backgroundColor:'#080f12',overflow:'hidden'}}>
    <CanvasImage src={staticFile('stadium.jpg')} style={{position:'absolute',width:1340,height:1984,left:-130,top:-20,opacity:.11,filter:'blur(9px) saturate(.3)'}}/>
    <CardSurface/>
    <Interactive.Div name="Listen on YouTube" style={{position:'absolute',left:98,top:320,color:PAPER,fontFamily:'Instrument',fontSize:105,lineHeight:.95,letterSpacing:-1.2,opacity:interpolate(frame,[0,13],[0,1],CLAMP)}}>
      full song’s<br/>on <i>YouTube.</i>
    </Interactive.Div>
    <div style={{position:'absolute',left:96,top:660,width:888,height:655,overflow:'hidden',boxShadow:'0 16px 55px #0006',border:'1px solid #d2d0c231',backgroundColor:'#101010',translate:interpolate(frame,[0,22],['0px 15px','0px 0px'],CLAMP),opacity:interpolate(frame,[2,18],[0,1],CLAMP)}}>
      <CanvasImage src={staticFile('youtube-thumbnail.jpg')} style={{position:'absolute',left:0,top:0,width:888,height:500}}/>
      <CanvasImage src={staticFile('youtube-channel.jpg')} style={{position:'absolute',left:29,top:527,width:310,height:90}}/>
      <svg width="56" height="40" viewBox="0 0 56 40" style={{position:'absolute',right:32,top:552}}><rect width="56" height="40" rx="11" fill="#c84536"/><path d="M23 11L39 20L23 29Z" fill="#f6eee1"/></svg>
    </div>
    <Interactive.Div name="Song name" style={{position:'absolute',left:98,right:90,top:1380,color:PAPER,fontFamily:'Instrument',fontSize:67,lineHeight:1.0}}>This must be heaven</Interactive.Div>
    <Interactive.Div name="Album name" style={{position:'absolute',left:102,top:1497,color:PAPER,fontFamily:'Archivo',fontSize:30,letterSpacing:6,opacity:.55}}>DUES COMPLEX</Interactive.Div>
    <AbsoluteFill style={{backgroundColor:'#080f12',opacity:interpolate(frame,[146,165],[0,1],CLAMP)}}/>
  </AbsoluteFill>;
};

export const StoryPromo = () => {
  const {fps} = useVideoConfig();
  return <AbsoluteFill style={{backgroundColor:'#080f12'}}>
    <Track name="Personal intro and YouTube ending">
      <Sequence name="A note from Veer" durationInFrames={5.5*fps}><Introduction/></Sequence>
      <Sequence name="Forty-eight seconds of the track" from={5.5*fps} durationInFrames={48*fps}>
        <Sequence name="Original film, starting eleven seconds in" from={-11*fps}><HeavenStory/></Sequence>
      </Sequence>
      <Sequence name="Full song on YouTube" from={53.5*fps} durationInFrames={5.5*fps}><YouTubeEnd/></Sequence>
    </Track>
    <Track name="Quiet instrumental under the cards">
      <Audio name="Intro instrumental" src={staticFile('intro-bed.wav')} durationInFrames={5.5*fps}/>
      <Audio name="Outro instrumental" src={staticFile('outro-bed.wav')} from={53.5*fps} durationInFrames={5.5*fps}/>
    </Track>
  </AbsoluteFill>;
};
