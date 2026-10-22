import {Composition} from 'remotion';
import {ScaffoldDiagnostics} from './scaffold/ScaffoldDiagnostics';
import {PremiumLesson} from './compositions/PremiumLesson';
import {demoLesson} from './lesson/demoLesson';
import {getLessonDurationInFrames} from './lesson/timeline';
import {lessonCanvas} from './design/theme';

// This registry remains strictly isolated from Python production stages.
// Step 2 adds only the lesson SHELL; Manim media remains for Step 3.
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
  </>
);
