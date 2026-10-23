import {Composition} from 'remotion';
import {ScaffoldDiagnostics} from './scaffold/ScaffoldDiagnostics';
import {PremiumLesson} from './compositions/PremiumLesson';
import {demoLesson} from './lesson/demoLesson';
import {getLessonDurationInFrames} from './lesson/timeline';
import {lessonCanvas} from './design/theme';
import {PremiumShort} from './compositions/PremiumShort';
import {getShortDurationInFrames, shortsCanvas} from './shorts/timeline';
import {NativeShort, nativeShortDuration} from './compositions/NativeShort';

// This registry remains strictly isolated from Python production stages.
// Landscape and vertical layouts share verified source packages.
export const RemotionRoot = () => (
  <>
    <Composition id="NativeShort" component={NativeShort}
      defaultProps={{title: 'Mathematics', label: 'One idea at a time', pages: [{
        durationInFrames: 60, videoSrc: 'native-shorts/preview.mp4',
        audioSrc: 'native-shorts/preview.mp3', captions: [{text: 'Portrait teaching preview',
          startMs: 0, endMs: 2000, timestampMs: 0, confidence: null}],
      }]}}
      calculateMetadata={({props}) => ({durationInFrames: nativeShortDuration(props)})}
      fps={30} width={1080} height={1920} durationInFrames={60}/>
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

