import {Composition} from 'remotion';
import {StoryPromo} from './Promo';

export const RemotionRoot = () => <Composition
  id="HeavenStory"
  component={StoryPromo}
  durationInFrames={1770}
  fps={30}
  width={1080}
  height={1920}
  defaultProps={{}}
/>;
