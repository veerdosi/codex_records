import {Composition} from 'remotion';
import {HeavenStory} from './Story';

export const RemotionRoot = () => <Composition
  id="HeavenStory"
  component={HeavenStory}
  durationInFrames={1770}
  fps={30}
  width={1080}
  height={1920}
  defaultProps={{}}
/>;
