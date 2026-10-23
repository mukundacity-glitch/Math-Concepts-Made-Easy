import {Recap} from './inverse/scenes/Recap';
import {Practice} from './inverse/scenes/Practice';
import {Notation} from './inverse/scenes/Notation';
import {Domain} from './inverse/scenes/Domain';
import {Graph} from './inverse/scenes/Graph';
import {Verify} from './inverse/scenes/Verify';
import {Algebra} from './inverse/scenes/Algebra';
import {Machine} from './inverse/scenes/Machine';
import {Opening} from './inverse/scenes/Opening';
import {InverseLesson} from './inverse/InverseLesson';
import {previewBeats, totalFrames, chapterRange} from './inverse/timeline';
import {validateMathBoards} from './inverse/boards';
import {Composition, Folder} from 'remotion';
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
    <Composition id="InverseFunctions" component={InverseLesson} defaultProps={{beats: previewBeats}}
      calculateMetadata={({props}) => {
        validateMathBoards(props.beats, 30);
        return {durationInFrames: totalFrames(props.beats)};
      }}
      fps={30} width={1920} height={1080} durationInFrames={totalFrames(previewBeats)}/>
    <Folder name="Inverse-scenes">
      <Composition id="Inverse-Opening" component={Opening} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'opening').duration}/>
      <Composition id="Inverse-Machine" component={Machine} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'machine').duration}/>
      <Composition id="Inverse-Algebra" component={Algebra} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'algebra').duration}/>
      <Composition id="Inverse-Verify" component={Verify} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'verify').duration}/>
      <Composition id="Inverse-Graph" component={Graph} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'graph').duration}/>
      <Composition id="Inverse-Domain" component={Domain} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'domain').duration}/>
      <Composition id="Inverse-Notation" component={Notation} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'notation').duration}/>
      <Composition id="Inverse-Practice" component={Practice} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'practice').duration}/>
      <Composition id="Inverse-Recap" component={Recap} defaultProps={{beats: previewBeats}}
        fps={30} width={1920} height={1080} durationInFrames={chapterRange(previewBeats, 'recap').duration}/>
    </Folder>
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

