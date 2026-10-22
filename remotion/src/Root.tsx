import {Composition} from 'remotion';
import {ScaffoldDiagnostics} from './scaffold/ScaffoldDiagnostics';
import {PremiumLesson} from './compositions/PremiumLesson';
import {demoLesson} from './lesson/demoLesson';
import {getLessonDurationInFrames} from './lesson/timeline';
import {lessonCanvas} from './design/theme';
import {PremiumShort} from './compositions/PremiumShort';
import {getShortDurationInFrames, shortsCanvas} from './shorts/timeline';

// This registry remains strictly isolated from Python production stages.
// Landscape and vertical layouts share verified source packages.
export const RemotionRoot = () => (
  <>
    <Composition
      id="ScaffoldDiagnostics"
      component={ScaffoldDiagnostics}
      fps={30}
      width={1920}
      height={1080}
      durationInFrames={30}
    />
    <Composition
      id="PremiumLesson"
      component={PremiumLesson}
      defaultProps={demoLesson}
      calculateMetadata={({props}) => ({
        durationInFrames: getLessonDurationInFrames(props),
      })}
      fps={lessonCanvas.fps}
      width={lessonCanvas.width}
      height={lessonCanvas.height}
      durationInFrames={getLessonDurationInFrames(demoLesson)}
    />
    <Composition
      id="PremiumShort"
      component={PremiumShort}
      defaultProps={demoLesson}
      calculateMetadata={({props}) => ({durationInFrames: getShortDurationInFrames(props)})}
      fps={shortsCanvas.fps}
      width={shortsCanvas.width}
      height={shortsCanvas.height}
      durationInFrames={getShortDurationInFrames(demoLesson)}
    />
  </>
);
